"""
Pipeline orchestration module for the University ETL.
Coordinates resolution, crawling, cleaning, extraction, normalization, and quality checks.
"""

import os
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import ValidationError

from src.models import (
    UniversityData, ExtractionResult, DataQualityReport, 
    Overview, Contact, Location, TuitionItem, AdmissionDeadline, PageMetadata
)
from src.resolver import resolve_university_input
from src.crawler import Crawler
from src.discovery import discover_relevant_pages
from src.cleaner import clean_html
from src.extractor import extract_university_data
from src.utils import setup_logger

logger = setup_logger(__name__)

def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Normalizes various date formats to YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()
    
    # Check if already YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
        
    # Attempt common parsing
    formats = [
        ("%B %d, %Y", re.compile(r'^[A-Za-z]+ \d{1,2}, \d{4}$')), # December 15, 2026
        ("%m/%d/%Y", re.compile(r'^\d{1,2}/\d{1,2}/\d{4}$')),    # 12/15/2026
        ("%Y/%m/%d", re.compile(r'^\d{4}/\d{2}/\d{2}$')),        # 2026/12/15
    ]
    
    for fmt, pattern in formats:
        if pattern.match(date_str):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
                
    # If standard parsing fails, return as-is
    return date_str

def normalize_currency(cost_val: Any) -> Optional[int]:
    """Normalizes cost values into pure integers (USD)."""
    if cost_val is None:
        return None
    if isinstance(cost_val, (int, float)):
        return int(cost_val)
        
    # If string, remove symbols, spaces, commas
    cleaned = re.sub(r'[^\d]', '', str(cost_val))
    if cleaned:
        try:
            return int(cleaned)
        except ValueError:
            pass
    return None

class UniversityETLPipeline:
    """ETL Pipeline orchestrator for extracting university admissions and tuition details."""
    
    def __init__(self):
        # Create output folder if missing
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def run_single(self, input_val: str) -> ExtractionResult:
        """Runs the ETL pipeline for a single university input (name or domain)."""
        logger.info(f"=== Starting ETL Pipeline for: {input_val} ===")
        
        # 1. Input Handling & Resolution
        try:
            domain = resolve_university_input(input_val)
            logger.info(f"Resolved domain for crawl: {domain}")
        except Exception as e:
            logger.critical(f"Input resolution failed: {e}")
            raise
            
        # 2. Crawling
        crawler = Crawler(domain, max_depth=2)
        crawled_pages = crawler.run()
        
        if not crawled_pages:
            logger.error("No pages crawled. Returning empty schema.")
            return ExtractionResult(data=UniversityData())
            
        # 3. Page Discovery & Selection
        top_admissions, top_tuition, home_pages = discover_relevant_pages(crawled_pages, top_n=3)
        
        # Combine pages (Admissions first, Tuition second, Home page last)
        selected_pages = []
        seen_urls = set()
        for p in top_admissions + top_tuition + home_pages:
            if p["url"] not in seen_urls:
                seen_urls.add(p["url"])
                selected_pages.append(p)
                
        # 4. Content Cleaning & Consolidation
        combined_text_blocks = []
        page_metadata_list = []
        
        for p in selected_pages:
            cleaned_text = clean_html(p["html"])
            # Format text segment with header indicator to help LLM recognize page context
            combined_text_blocks.append(f"--- PAGE TITLE: {p['title']} ({p['url']}) ---\n{cleaned_text}")
            
            # Map scraped page details into Pydantic schema structure
            page_metadata_list.append(PageMetadata(
                url=p["url"],
                page_title=p["title"],
                scraped_at=p["scraped_at"],
                status_code=p["status_code"]
            ))
            
        combined_text = "\n\n".join(combined_text_blocks)
        source_urls = [p["url"] for p in selected_pages]
        
        # 5. Gemini Data Extraction (maximum 1 main call per university)
        extracted_raw = {}
        try:
            extracted_raw = extract_university_data(combined_text, source_urls)
        except Exception as e:
            logger.error(f"Gemini data extraction failed: {e}")
            
        # 6. Schema Parsing, Normalization, & Quality Checks
        quality_report = DataQualityReport()
        
        # Helper to track missing fields
        missing_fields = []
        invalid_formats = []
        duplicates_found = []
        
        # Normalize tuition breakdown items
        normalized_tuition = []
        seen_tuition = set()
        for item in extracted_raw.get("tuition_breakdown", []):
            fee_type = item.get("fee_type")
            cost = normalize_currency(item.get("cost"))
            currency = item.get("currency", "USD")
            
            if not fee_type or cost is None:
                invalid_formats.append(f"Invalid TuitionItem: {item}")
                continue
                
            # Check duplicates
            dedup_key = f"{fee_type.lower()}_{cost}"
            if dedup_key in seen_tuition:
                duplicates_found.append(f"Duplicate tuition item: {fee_type} (${cost})")
                continue
            seen_tuition.add(dedup_key)
            
            normalized_tuition.append(TuitionItem(
                fee_type=fee_type,
                cost=cost,
                currency=currency
            ))
            
        # Normalize admission deadlines
        normalized_deadlines = []
        seen_deadlines = set()
        for item in extracted_raw.get("admission_deadlines", []):
            deadline_type = item.get("deadline_type")
            raw_date = item.get("deadline_date")
            normalized_date_val = normalize_date(raw_date)
            notes = item.get("notes")
            
            # Date validation
            if normalized_date_val and not re.match(r'^\d{4}-\d{2}-\d{2}$', normalized_date_val):
                invalid_formats.append(f"Invalid date format: '{raw_date}' in deadline")
                
            dedup_key = f"{deadline_type}_{normalized_date_val}"
            if dedup_key in seen_deadlines:
                duplicates_found.append(f"Duplicate deadline item: {deadline_type} ({normalized_date_val})")
                continue
            seen_deadlines.add(dedup_key)
            
            normalized_deadlines.append(AdmissionDeadline(
                deadline_type=deadline_type,
                deadline_date=normalized_date_val,
                notes=notes
            ))
            
        # Overview extraction and formatting checks
        raw_overview = extracted_raw.get("overview", {})
        uni_name = raw_overview.get("university_name")
        if not uni_name:
            missing_fields.append("overview.university_name")
            
        raw_loc = raw_overview.get("location", {})
        location_obj = Location(
            city=raw_loc.get("city"),
            state=raw_loc.get("state"),
            country=raw_loc.get("country"),
            postal_code=raw_loc.get("postal_code")
        )
        
        raw_contact = raw_overview.get("contact", {})
        email_val = raw_contact.get("email")
        if email_val:
            # Pydantic EmailStr does validate email, let's catch it if it fails
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email_val):
                invalid_formats.append(f"Invalid email pattern: {email_val}")
                email_val = None
                
        contact_obj = Contact(
            phone=raw_contact.get("phone"),
            email=email_val
        )
        
        overview_obj = Overview(
            university_name=uni_name,
            location=location_obj,
            contact=contact_obj
        )
        
        # Build strict UniversityData schema instance
        try:
            uni_data = UniversityData(
                overview=overview_obj,
                tuition_breakdown=normalized_tuition,
                admission_deadlines=normalized_deadlines,
                page_metadata=page_metadata_list
            )
        except ValidationError as e:
            logger.error(f"Pydantic Validation failed: {e}")
            quality_report.is_valid = False
            invalid_formats.append(str(e))
            uni_data = UniversityData()
            
        # Finalize Quality Report details
        quality_report.missing_fields = missing_fields
        quality_report.invalid_formats = invalid_formats
        quality_report.duplicates_found = duplicates_found
        
        confidence_scores = extracted_raw.get("confidence_scores", {})
        source_attributions = extracted_raw.get("source_attributions", {})
        
        result = ExtractionResult(
            data=uni_data,
            confidence_scores=confidence_scores,
            source_attributions=source_attributions,
            quality_report=quality_report
        )
        
        # Save output to outputs folder
        cleaned_filename = re.sub(r'[^\w\-_]', '_', input_val.replace("https://", "").replace("www.", ""))
        output_file = os.path.join(self.output_dir, f"{cleaned_filename}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
            
        logger.info(f"ETL completed successfully. Output saved to {output_file}")
        return result

    def run_batch(self, inputs: List[str]) -> Dict[str, ExtractionResult]:
        """Runs the ETL pipeline for a list/batch of university inputs."""
        results = {}
        for input_val in inputs:
            try:
                results[input_val] = self.run_single(input_val)
            except Exception as e:
                logger.error(f"Batch processing failed for '{input_val}': {e}")
        return results
