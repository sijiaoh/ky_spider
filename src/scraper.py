import logging
import time
from typing import List, Dict, Tuple

from playwright.sync_api import sync_playwright, Browser, Page

from .config import ScrapingConfig, TableConfig


logger = logging.getLogger(__name__)


class FinancialDataScraper:
    """Scraper for financial data from Eastmoney website"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        
    def _retry_operation(self, operation, operation_name: str, max_retries: int = 3, retry_delay: int = 2000):
        """Execute operation with retry logic"""
        for attempt in range(max_retries):
            try:
                operation()
                return
            except Exception as e:
                logger.warning(f"{operation_name} attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Failed {operation_name} after {max_retries} attempts")
                    raise RuntimeError(f"Failed {operation_name} after {max_retries} attempts")
                # Wait before retry
                time.sleep(retry_delay / 1000)
        
    def _setup_browser(self) -> tuple[Browser, Page]:
        """Initialize browser and page"""
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=self.config.headless)
        page = browser.new_page()
        page.set_default_timeout(self.config.timeout)
        return browser, page
    
    
    
    
    def _scrape_single_table(self, page: Page, table_config: TableConfig) -> List[str]:
        """Scrape all pages from a single table configuration"""
        html_pages = []
        
        # Click button if specified
        if table_config.button_selector:
            def click_button():
                logger.info(f"Clicking button: {table_config.button_selector}")
                button = page.query_selector(table_config.button_selector)
                if not button:
                    logger.error(f"Button not found: {table_config.button_selector}")
                    raise RuntimeError(f"Button not found: {table_config.button_selector}")
                button.click()
                page.wait_for_load_state('networkidle')
            
            self._retry_operation(click_button, f"button click for {table_config.button_selector}")
        
        # Wait for table to load
        def wait_for_table():
            logger.info(f"Waiting for table to load: {table_config.table_selector}")
            page.wait_for_selector(table_config.table_selector, timeout=self.config.timeout)
            logger.info("Table loaded successfully")
        
        self._retry_operation(wait_for_table, f"table load for {table_config.table_selector}")
        
        page_count = 0
        while True:
            logger.info(f"Scraping page {page_count + 1} for table {table_config.table_selector}")
            html_pages.append(page.content())
            
            # Check for next button
            next_button = page.query_selector(table_config.pagination_selector)
            if not next_button or not next_button.is_visible():
                logger.info(f"No more pages found. Total pages: {page_count + 1}")
                break
            
            # Store current table state for comparison
            current_table = page.query_selector(table_config.table_container_selector)
            if not current_table:
                logger.error(f"Critical error: Table disappeared during pagination: {table_config.table_container_selector}")
                raise RuntimeError(f"Table not found during pagination: {table_config.table_container_selector}")
                
            current_html = current_table.inner_html()
            
            # Click next button and wait for content update with retry
            def navigate_next_page():
                next_button.click()
                page.wait_for_load_state('networkidle')
                page.wait_for_function(
                    f"""
                    (oldHtml) => {{
                        const table = document.querySelector("{table_config.table_container_selector}");
                        return table && table.innerHTML !== oldHtml;
                    }}
                    """,
                    arg=current_html,
                    timeout=self.config.timeout
                )
            
            self._retry_operation(navigate_next_page, "pagination", max_retries=3, retry_delay=1000)
            page_count += 1
            
        return html_pages

    def _scrape_single_url(self, page: Page, url: str) -> Dict[str, List[str]]:
        """Scrape all tables from a single URL"""
        # Initial page load with retry
        def load_page():
            logger.info(f"Loading initial page from {url}")
            page.goto(url, wait_until='networkidle')
            logger.info("Page loaded successfully")
        
        self._retry_operation(load_page, f"page load for {url}")
        
        table_results = {}
        for i, table_config in enumerate(self.config.tables):
            table_name = f"table_{i}"
            logger.info(f"Processing {table_name} with selector: {table_config.table_selector}")
            
            try:
                html_pages = self._scrape_single_table(page, table_config)
                if not html_pages:
                    logger.error(f"Critical error: No pages scraped for {table_name}")
                    raise RuntimeError(f"No data scraped for {table_name}")
                table_results[table_name] = html_pages
                logger.info(f"Successfully scraped {len(html_pages)} pages for {table_name}")
            except Exception as e:
                logger.error(f"Failed to scrape {table_name}: {e}")
                raise
            
        return table_results
    
    def scrape_data(self, urls: List[str] = None) -> Dict[str, Dict[str, List[str]]]:
        """Scrape data from multiple URLs using single browser instance"""
        if urls is None:
            urls = [self.config.full_url]
            
        # 去重URL，保持原始顺序
        urls = list(dict.fromkeys(urls))
        logger.info(f"Processing {len(urls)} unique URLs")
            
        results = {}
        browser, page = self._setup_browser()
        
        try:
            for url in urls:
                logger.info(f"Starting to scrape {url}")
                table_data = self._scrape_single_url(page, url)
                if not table_data:
                    logger.error(f"Critical error: No tables scraped from {url}")
                    raise RuntimeError(f"No data scraped from {url} - operation cannot continue")
                results[url] = table_data
                logger.info(f"Successfully scraped {len(table_data)} tables from {url}")
        finally:
            browser.close()
                
        return results
    
    
    def run(self, urls: List[str] = None) -> Dict[str, Dict[str, List[str]]]:
        """Main method to run the scraping process and return HTML data"""
        scraped_data = self.scrape_data(urls)
        
        # Verify we have data before returning
        if not scraped_data or all(not table_data for table_data in scraped_data.values()):
            logger.error("Critical error: No data scraped from any URL")
            raise RuntimeError("No data scraped - operation failed")
        
        logger.info("Scraping process completed successfully")
        return scraped_data
