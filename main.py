#!/usr/bin/env python3
"""
Financial Data Scraper for Eastmoney Website

This script scrapes financial data from Eastmoney's website and exports it to Excel.
"""

import sys
from src.interfaces.cli import cli_main


if __name__ == "__main__":
    sys.exit(cli_main())
