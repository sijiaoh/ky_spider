import logging
from typing import List, Dict
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, Page
import pandas as pd
from io import StringIO

from .config import ScrapingConfig


logger = logging.getLogger(__name__)


class FinancialDataScraper:
    """Scraper for financial data from Eastmoney website"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        
    def _setup_browser(self) -> tuple[Browser, Page]:
        """Initialize browser and page"""
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=self.config.headless)
        page = browser.new_page()
        page.set_default_timeout(self.config.timeout)
        return browser, page
    
    def _extract_page_data(self, html_content: str, page_index: int) -> pd.DataFrame:
        """Extract table data from HTML content"""
        soup = BeautifulSoup(html_content, "lxml")
        
        title = soup.select_one("title")
        if title:
            logger.info(f"Processing page {page_index}: {title.text.strip()}")
        
        zyzb_table = soup.select_one(".zyzb_table .report_table .table1")
        if not zyzb_table:
            logger.error(f"Critical error: No table found on page {page_index}")
            raise RuntimeError(f"Table not found on page {page_index} - data integrity compromised")
        
        df = pd.read_html(StringIO(str(zyzb_table)))[0]
        
        if df.empty:
            logger.error(f"Critical error: Empty table data on page {page_index}")
            raise RuntimeError(f"Empty table data on page {page_index} - data integrity compromised")
        
        # Remove first column for non-first pages to avoid duplication
        if page_index > 0:
            df = df.iloc[:, 1:]
        
        return df
    
    def _scrape_single_url(self, url: str) -> List[str]:
        """Scrape all pages from a single URL"""
        html_pages = []
        
        browser, page = self._setup_browser()
        
        try:
            page_count = 0
            while True:
                logger.info(f"Scraping page {page_count + 1} from {url}")
                page.goto(url)
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
                
                # Wait for table to update
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
                    
        finally:
            browser.close()
            
        return html_pages
    
    def scrape_data(self, urls: List[str] = None) -> Dict[str, List[str]]:
        """Scrape data from multiple URLs"""
        if urls is None:
            urls = [self.config.full_url]
            
        results = {}
        
        for url in urls:
            logger.info(f"Starting to scrape {url}")
            html_pages = self._scrape_single_url(url)
            if not html_pages:
                logger.error(f"Critical error: No pages scraped from {url}")
                raise RuntimeError(f"No data scraped from {url} - operation cannot continue")
            results[url] = html_pages
            logger.info(f"Successfully scraped {len(results[url])} pages from {url}")
                
        return results
    
    def process_and_save_data(self, scraped_data: Dict[str, List[str]]) -> None:
        """Process scraped HTML data and save to Excel"""
        self.config.output_dir.mkdir(exist_ok=True)
        
        for url, html_pages in scraped_data.items():
            if not html_pages:
                logger.error(f"Critical error: No data to process for {url}")
                raise RuntimeError(f"No data available for processing from {url}")
                
            tables = []
            
            for i, html_content in enumerate(html_pages):
                df = self._extract_page_data(html_content, i)
                tables.append(df)
            
            # Combine all tables horizontally
            combined_df = pd.concat(tables, axis=1, ignore_index=True)
            
            if combined_df.empty:
                logger.error(f"Critical error: Combined dataframe is empty for {url}")
                raise RuntimeError(f"Final dataframe is empty for {url}")
            
            combined_df.to_excel(self.config.output_path, index=False)
            logger.info(f"Data saved to {self.config.output_path}")
            
            # Verify file was created and has content
            if not self.config.output_path.exists():
                logger.error(f"Critical error: Output file not created: {self.config.output_path}")
                raise RuntimeError(f"Failed to create output file: {self.config.output_path}")
            
            if self.config.output_path.stat().st_size == 0:
                logger.error(f"Critical error: Output file is empty: {self.config.output_path}")
                raise RuntimeError(f"Output file is empty: {self.config.output_path}")
    
    def run(self, urls: List[str] = None) -> None:
        """Main method to run the complete scraping process"""
        scraped_data = self.scrape_data(urls)
        
        # Verify we have data before processing
        if not scraped_data or all(not pages for pages in scraped_data.values()):
            logger.error("Critical error: No data scraped from any URL")
            raise RuntimeError("No data scraped - operation failed")
        
        self.process_and_save_data(scraped_data)
        logger.info("Scraping process completed successfully")