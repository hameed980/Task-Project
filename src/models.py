"""
Pydantic schemas for university data extraction and quality reporting.
Contains the official UniversityData schemas and pipeline wrappers.
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr, Field


# --- Official Pydantic Schema Provided by User ---

class Location(BaseModel):
    city:        Optional[str] = None
    state:       Optional[str] = None
    country:     Optional[str] = None
    postal_code: Optional[str] = None


class Contact(BaseModel):
    phone: Optional[str]      = None
    email: Optional[EmailStr] = None


class Overview(BaseModel):
    university_name: Optional[str]      = None
    location:        Optional[Location] = None
    contact:         Optional[Contact]  = None


class TuitionItem(BaseModel):
    fee_type: Optional[str] = None
    cost:     Optional[int] = None    # whole number, USD
    currency: Optional[str] = None


class DeadlineType(str, Enum):
    EARLY_DECISION     = "Early Decision"
    REGULAR_DECISION   = "Regular Decision"
    TRANSFER_ADMISSION = "Transfer Admission"


class AdmissionDeadline(BaseModel):
    deadline_type: Optional[DeadlineType] = None
    deadline_date: Optional[str]          = None
    notes:         Optional[str]          = None


class PageMetadata(BaseModel):
    url:         Optional[str] = None
    page_title:  Optional[str] = None
    scraped_at:  Optional[str] = None
    status_code: Optional[str] = None


class UniversityData(BaseModel):
    overview:            Optional[Overview]      = None
    tuition_breakdown:   List[TuitionItem]       = []
    admission_deadlines: List[AdmissionDeadline] = []
    page_metadata:       List[PageMetadata]      = []


# --- Pipeline Metadata & Verification Schemas ---

class DataQualityReport(BaseModel):
    """Holds data validation and quality check metrics."""
    missing_fields: List[str] = Field(default_factory=list, description="Fields that were expected but returned null/empty")
    invalid_formats: List[str] = Field(default_factory=list, description="Format errors identified during extraction or parsing")
    duplicates_found: List[str] = Field(default_factory=list, description="Duplicate items identified and deduplicated")
    is_valid: bool = Field(default=True, description="True if no severe format violations occurred")


class ExtractionResult(BaseModel):
    """Final wrapped output for a university extraction process."""
    data: UniversityData
    confidence_scores: Dict[str, float] = Field(
        default_factory=dict, 
        description="Confidence scores (0.0 to 1.0) mapped to fields/nodes"
    )
    source_attributions: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Source URLs attributed to specific extracted values"
    )
    quality_report: DataQualityReport = Field(default_factory=DataQualityReport)
