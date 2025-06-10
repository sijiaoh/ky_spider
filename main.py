#!/usr/bin/env python3
"""
Financial Data Scraper for Eastmoney Website

This script scrapes financial data from Eastmoney's website and exports it to Excel.
"""

import argparse
import sys
from pathlib import Path

from src.config import ScrapingConfig
from src.scraper import FinancialDataScraper
from src.utils import setup_logging


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Scrape financial data from Eastmoney website"
    )
    parser.add_argument(
        "--stock-code",
        default="SH605136",
        help="Stock code to scrape (default: SH605136)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build"),
        help="Output directory (default: build)"
    )
    parser.add_argument(
        "--output-file",
        default="zyzb_table.xlsx",
        help="Output filename (default: zyzb_table.xlsx)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Log file path (optional)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10000,
        help="Page timeout in milliseconds (default: 10000)"
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point"""
    try:
        args = parse_arguments()
        
        # Setup logging
        setup_logging(args.log_level, args.log_file)
        
        # Create configuration
        config = ScrapingConfig(
            stock_code=args.stock_code,
            output_dir=args.output_dir,
            output_filename=args.output_file,
            headless=args.headless,
            timeout=args.timeout
        )
        
        # Create and run scraper
        scraper = FinancialDataScraper(config)
        scraper.run()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        return 1
    except Exception as e:
        print(f"Critical Error: {e}", file=sys.stderr)
        print("Process terminated due to data integrity failure", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
