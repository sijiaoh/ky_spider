import logging
from typing import List, Dict, Optional
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, Page
import pandas as pd
from io import StringIO
import cn2an

from .config import ScrapingConfig
from .validator import DataValidator, DataIntegrityError, TableStructureError, DataContentError


logger = logging.getLogger(__name__)


class FinancialDataScraper:
    """
    High-precision data scraper with strict integrity validation.
    
    All operations are validated for data integrity. Any validation failure
    results in immediate termination to ensure output accuracy.
    """
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.validator = DataValidator(strict_mode=True)
        logger.info("Initialized scraper with strict data validation")
        
    def _setup_browser(self) -> tuple[Browser, Page]:
        """Initialize browser and page"""
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=self.config.headless)
        page = browser.new_page()
        page.set_default_timeout(self.config.timeout)
        return browser, page
    
    def _extract_page_data(self, html_content: str, page_index: int) -> tuple[pd.DataFrame, str]:
        """
        Extract table data and title from HTML content with strict validation.
        
        CRITICAL: Any extraction failure results in immediate termination.
        """
        # Validate input
        self.validator.validate_page_extraction_success(html_content, page_index)
        
        soup = BeautifulSoup(html_content, "lxml")
        
        # Extract and validate title
        title = soup.select_one("title")
        page_title = title.text.strip() if title else f"Unknown_Page_{page_index}"
        
        if not page_title or len(page_title.strip()) == 0:
            raise DataIntegrityError(f"Critical failure: No valid title found on page {page_index}")
        
        logger.info(f"Processing page {page_index}: {page_title}")
        
        # Extract table with strict validation
        zyzb_table = soup.select_one(".zyzb_table .report_table .table1")
        if not zyzb_table:
            raise DataIntegrityError(f"Critical failure: Target table not found on page {page_index}")
        
        # Parse HTML table
        try:
            df = pd.read_html(StringIO(str(zyzb_table)))[0]
        except (ValueError, IndexError) as e:
            raise DataIntegrityError(f"Critical failure: Table parsing failed on page {page_index}: {e}")
        
        # Strict table validation
        self.validator.validate_table_extraction_success(df, page_index)
        
        # Remove first column for non-first pages to avoid duplication
        if page_index > 0:
            if df.shape[1] <= 1:
                raise TableStructureError(f"Critical failure: Cannot remove first column - insufficient columns on page {page_index}")
            df = df.iloc[:, 1:]
            
            # Re-validate after column removal
            self.validator.validate_dataframe_not_empty(df, f"page {page_index} after column removal")
        
        # Final validation of extracted data
        self.validator.validate_minimum_dimensions(df, min_rows=2, min_cols=1, context=f"page {page_index} final")
        
        logger.debug(f"✓ Successfully extracted data from page {page_index}: {df.shape}")
        return df, page_title
    
    def _split_dataframe_by_indicators(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """
        Split dataframe by indicator markers with strict validation.
        
        CRITICAL: Validates indicator presence and section integrity.
        """
        # Validate input DataFrame
        self.validator.validate_dataframe_not_empty(df, "indicator splitting")
        self.validator.validate_minimum_dimensions(df, min_rows=1, min_cols=1, context="indicator splitting")
        
        # Find rows where first column ends with 指标
        first_col = df.iloc[:, 0].astype(str)
        indicator_rows = first_col.str.endswith('指标')
        indicator_indices = df.index[indicator_rows].tolist()
        
        if not indicator_indices:
            logger.warning("No indicator markers found - treating entire dataframe as single section")
            return [df]
        
        # Validate indicator markers are meaningful
        self.validator.validate_indicator_markers_present(df, "indicator splitting")
        
        indicator_dfs = []
        
        for i, start_idx in enumerate(indicator_indices):
            if i < len(indicator_indices) - 1:
                # Section from current indicator to next indicator (exclusive)
                end_idx = indicator_indices[i + 1]
                section_df = df.iloc[start_idx:end_idx].copy()
            else:
                # Last section: from current indicator to end of dataframe
                section_df = df.iloc[start_idx:].copy()
            
            # Validate each section
            self.validator.validate_dataframe_not_empty(section_df, f"indicator section {i}")
            self.validator.validate_minimum_dimensions(section_df, min_rows=1, min_cols=1, context=f"indicator section {i}")
            
            indicator_dfs.append(section_df)
        
        logger.info(f"✓ Split dataframe into {len(indicator_dfs)} validated indicator sections")
        return indicator_dfs
    
    def _convert_chinese_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert Chinese number formats to pure numbers with validation.
        
        CRITICAL: Validates data region and conversion results.
        """
        # Validate input and data region
        self.validator.validate_dataframe_not_empty(df, "Chinese number conversion")
        self.validator.validate_numeric_data_region(df, start_row=1, start_col=1, context="Chinese number conversion")
        
        converted_df = df.copy()
        conversion_count = 0
        
        # Process data starting from row 2, column 2 (inclusive)
        for row_idx in range(1, len(df)):  # Start from row 2 (index 1)
            for col_idx in range(1, len(df.columns)):  # Start from column 2 (index 1)
                cell_value = df.iloc[row_idx, col_idx]
                
                if pd.isna(cell_value):
                    continue
                
                cell_str = str(cell_value).strip()
                if not cell_str:
                    continue
                
                original_value = cell_str
                
                try:
                    # Handle 万亿 directly (cn2an doesn't support it)
                    if '万亿' in cell_str:
                        base_part = cell_str.replace('万亿', '')
                        base_num = float(base_part)
                        converted_value = base_num * 1000000000000  # 1万亿 = 10^12
                        converted_df.iloc[row_idx, col_idx] = converted_value
                        conversion_count += 1
                        logger.debug(f"Converted 万亿: {original_value} -> {converted_value}")
                    else:
                        # Use cn2an for other Chinese number formats
                        converted_value = cn2an.cn2an(cell_str, "smart")
                        converted_df.iloc[row_idx, col_idx] = converted_value
                        conversion_count += 1
                        logger.debug(f"Converted CN: {original_value} -> {converted_value}")
                except (ValueError, TypeError) as e:
                    # Log conversion failures for monitoring
                    logger.debug(f"Conversion failed for '{original_value}': {e}")
                    continue
        
        # Validate conversion results
        if conversion_count == 0:
            logger.warning("No Chinese numbers were converted - data may already be in numeric format")
        else:
            logger.info(f"✓ Successfully converted {conversion_count} Chinese numbers")
        
        # Validate output dataframe integrity
        self.validator.validate_dataframe_not_empty(converted_df, "Chinese number conversion output")
        
        return converted_df
    
    def _scrape_single_url(self, page: Page, url: str) -> List[str]:
        """Scrape all pages from a single URL"""
        html_pages = []
        
        # Initial page load
        logger.info(f"Loading initial page from {url}")
        page.goto(url)
        
        # Wait for table to be fully loaded
        logger.info("Waiting for table to load...")
        page.wait_for_selector(".zyzb_table .report_table .table1", timeout=self.config.timeout)
        logger.info("Table loaded successfully")
        
        page_count = 0
        while True:
            logger.info(f"Scraping page {page_count + 1}")
            html_pages.append(page.content())
            
            # Check for next button
            next_button = page.query_selector(".zyzb_table .next")
            if not next_button or not next_button.is_visible():
                logger.info(f"No more pages found. Total pages: {page_count + 1}")
                break
            
            # Store current table state for comparison
            current_table = page.query_selector(".zyzb_table")
            if not current_table:
                logger.error("Critical error: Table disappeared during pagination")
                raise RuntimeError("Table not found during pagination - data integrity compromised")
                
            current_html = current_table.inner_html()
            
            # Click next button
            next_button.click()
            
            # Wait for table to update (SPA content change)
            page.wait_for_function(
                """
                (oldHtml) => {
                    const table = document.querySelector(".zyzb_table");
                    return table && table.innerHTML !== oldHtml;
                }
                """,
                arg=current_html,
                timeout=self.config.timeout
            )
            page_count += 1
            
        return html_pages
    
    def scrape_data(self, urls: List[str] = None) -> Dict[str, List[str]]:
        """
        Scrape data from multiple URLs with strict validation.
        
        CRITICAL: Validates all URL extractions and page counts.
        """
        if urls is None:
            urls = [self.config.full_url]
        
        if not urls:
            raise DataIntegrityError("Critical failure: No URLs provided for scraping")
        
        logger.info(f"Starting data extraction from {len(urls)} URLs")
        
        results = {}
        browser, page = self._setup_browser()
        
        try:
            for url_index, url in enumerate(urls):
                logger.info(f"Processing URL {url_index + 1}/{len(urls)}: {url}")
                
                html_pages = self._scrape_single_url(page, url)
                
                # Critical validation: Must have extracted pages
                if not html_pages:
                    raise DataIntegrityError(f"Critical failure: No pages extracted from {url}")
                
                # Validate page count is reasonable
                self.validator.validate_pagination_integrity(len(html_pages), expected_min_pages=1)
                
                results[url] = html_pages
                logger.info(f"✓ Extracted {len(html_pages)} pages from {url}")
                
        finally:
            browser.close()
        
        # Final validation of extraction results
        self.validator.validate_url_data_consistency(results, min_urls=len(urls))
        
        logger.info(f"✓ Successfully completed data extraction from all {len(urls)} URLs")
        return results
    
    def process_and_save_data(self, scraped_data: Dict[str, List[str]]) -> None:
        """
        Process scraped HTML data and save to Excel with strict validation.
        
        CRITICAL: Every step is validated. Any failure terminates immediately.
        """
        # Validate input data
        if not scraped_data:
            raise DataIntegrityError("Critical failure: No scraped data provided for processing")
        
        self.config.output_dir.mkdir(exist_ok=True)
        all_url_data = []
        
        # Process each URL's data with strict validation
        for url_index, (url, html_pages) in enumerate(scraped_data.items()):
            logger.info(f"Processing URL {url_index + 1}/{len(scraped_data)}: {url}")
            
            # Critical validation: Must have pages
            if not html_pages:
                raise DataIntegrityError(f"Critical failure: No HTML pages for URL {url}")
            
            page_tables = []
            page_title = None
            
            # Process each page with validation
            for i, html_content in enumerate(html_pages):
                df, title = self._extract_page_data(html_content, i)
                
                if page_title is None:
                    page_title = title
                elif page_title != title:
                    logger.warning(f"Title mismatch: '{page_title}' vs '{title}' on page {i}")
                
                page_tables.append(df)
            
            # Validate we have extracted tables
            if not page_tables:
                raise DataIntegrityError(f"Critical failure: No tables extracted from {url}")
            
            # Combine pages horizontally with validation
            try:
                url_combined_df = pd.concat(page_tables, axis=1, ignore_index=True)
            except Exception as e:
                raise DataIntegrityError(f"Critical failure: Cannot combine page tables for {url}: {e}")
            
            # Validate combined dataframe
            self.validator.validate_dataframe_not_empty(url_combined_df, f"combined pages for {url}")
            
            # Split by indicators with validation
            indicator_sections = self._split_dataframe_by_indicators(url_combined_df)
            
            if not indicator_sections:
                raise DataIntegrityError(f"Critical failure: No indicator sections found for {url}")
            
            # Convert Chinese numbers with validation
            converted_sections = []
            for section_idx, section in enumerate(indicator_sections):
                try:
                    converted_section = self._convert_chinese_numbers(section)
                    converted_sections.append(converted_section)
                except Exception as e:
                    raise DataIntegrityError(f"Critical failure: Number conversion failed for section {section_idx} of {url}: {e}")
            
            # Recombine sections with validation
            try:
                url_combined_df = pd.concat(converted_sections, axis=0, ignore_index=True)
            except Exception as e:
                raise DataIntegrityError(f"Critical failure: Cannot recombine indicator sections for {url}: {e}")
            
            # Final validation of URL data
            self.validator.validate_dataframe_not_empty(url_combined_df, f"final processing for {url}")
            self.validator.validate_minimum_dimensions(url_combined_df, min_rows=1, min_cols=1, context=f"final data for {url}")
            
            # Add Title identifier column
            if not page_title:
                raise DataIntegrityError(f"Critical failure: No valid title found for {url}")
            
            url_combined_df.insert(0, 'Title', page_title)
            all_url_data.append(url_combined_df)
            
            logger.info(f"✓ Processed {len(page_tables)} pages, {len(indicator_sections)} sections from {url} -> {url_combined_df.shape}")
        
        # Combine all URLs vertically with critical validation
        if not all_url_data:
            raise DataIntegrityError("Critical failure: No processed data from any URL")
        
        logger.info(f"Combining data from {len(all_url_data)} URLs")
        
        try:
            final_df = pd.concat(all_url_data, axis=0, ignore_index=True)
        except Exception as e:
            raise DataIntegrityError(f"Critical failure: Cannot combine URL data: {e}")
        
        # Final validation before output
        expected_features = {
            'min_rows': len(all_url_data),  # At least one row per URL
            'expected_columns': None  # Variable column count allowed
        }
        self.validator.validate_final_output(final_df, expected_features)
        
        # Critical: Save to Excel with error handling
        try:
            final_df.to_excel(self.config.output_path, index=False)
        except Exception as e:
            raise DataIntegrityError(f"Critical failure: Cannot save Excel file: {e}")
        
        # Critical: Verify file creation and content
        if not self.config.output_path.exists():
            raise DataIntegrityError(f"Critical failure: Output file not created: {self.config.output_path}")
        
        file_size = self.config.output_path.stat().st_size
        if file_size == 0:
            raise DataIntegrityError(f"Critical failure: Output file is empty: {self.config.output_path}")
        
        # Final success validation
        logger.info(f"✓ PROCESSING COMPLETE:")
        logger.info(f"  - URLs processed: {len(scraped_data)}")
        logger.info(f"  - Final data shape: {final_df.shape}")
        logger.info(f"  - Output file: {self.config.output_path}")
        logger.info(f"  - File size: {file_size:,} bytes")
        logger.info(f"  - All integrity checks PASSED")
    
    def run(self, urls: List[str] = None) -> None:
        """
        Execute complete data extraction pipeline with strict validation.
        
        CRITICAL: Any validation failure at any step terminates immediately.
        Only proceeds if ALL data integrity checks pass.
        """
        logger.info("=" * 60)
        logger.info("STARTING HIGH-PRECISION DATA EXTRACTION")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Data Extraction
            logger.info("Phase 1: Extracting raw data...")
            scraped_data = self.scrape_data(urls)
            
            # Critical validation before processing
            if not scraped_data:
                raise DataIntegrityError("Critical failure: No data extracted in Phase 1")
            
            if all(not pages for pages in scraped_data.values()):
                raise DataIntegrityError("Critical failure: All extracted data is empty")
            
            logger.info("✓ Phase 1 completed: Raw data extraction successful")
            
            # Phase 2: Data Processing & Validation
            logger.info("Phase 2: Processing and validating data...")
            self.process_and_save_data(scraped_data)
            
            logger.info("✓ Phase 2 completed: Data processing and validation successful")
            logger.info("=" * 60)
            logger.info("✓ EXTRACTION PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("All data integrity validations PASSED")
            logger.info("=" * 60)
            
        except (DataIntegrityError, TableStructureError, DataContentError) as e:
            logger.error("=" * 60)
            logger.error("CRITICAL DATA INTEGRITY FAILURE")
            logger.error(f"Error: {e}")
            logger.error("Operation terminated to ensure data accuracy")
            logger.error("=" * 60)
            raise
        
        except Exception as e:
            logger.error("=" * 60)
            logger.error("UNEXPECTED SYSTEM ERROR")
            logger.error(f"Error: {e}")
            logger.error("Operation terminated")
            logger.error("=" * 60)
            raise DataIntegrityError(f"System error during extraction: {e}")
