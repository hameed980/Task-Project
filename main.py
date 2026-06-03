"""
Command-line interface for the University ETL Data Extraction Pipeline.
"""

import argparse
import sys
import json
from dotenv import load_dotenv
from src.pipeline import UniversityETLPipeline
from src.utils import setup_logger

load_dotenv()
logger = setup_logger("main")

def main():
    parser = argparse.ArgumentParser(
        description="Production-quality AI-powered University ETL pipeline."
    )
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--input", 
        type=str, 
        help="A single university name or official domain (e.g., 'Bucknell University' or 'https://www.bucknell.edu')"
    )
    group.add_argument(
        "--batch", 
        type=str, 
        help="Comma-separated list of university names or domains for batch processing"
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = UniversityETLPipeline()
    
    # If no arguments are provided, prompt user interactively
    if not args.input and not args.batch:
        try:
            user_input = input("Enter university name or domain (or press Enter to exit): ").strip()
            if not user_input:
                logger.info("No input provided. Exiting.")
                return
            args.input = user_input
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return

    if args.input:
        try:
            result = pipeline.run_single(args.input)
            print("\n=== EXTRACTED DATA RESULT ===")
            print(json.dumps(result.model_dump(), indent=2))
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            sys.exit(1)
            
    elif args.batch:
        inputs = [item.strip() for item in args.batch.split(",") if item.strip()]
        logger.info(f"Triggering batch execution for {len(inputs)} universities: {inputs}")
        try:
            results = pipeline.run_batch(inputs)
            print("\n=== BATCH PROCESSING SUMMARY ===")
            for uni, res in results.items():
                print(f"- {uni}: status_valid={res.quality_report.is_valid}, deadlines={len(res.data.admission_deadlines)}, fees={len(res.data.tuition_breakdown)}")
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
