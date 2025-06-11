import logging
from typing import List, Dict

from playwright.sync_api import sync_playwright, Browser, Page

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
    
    
    
    
    def _scrape_single_url(self, page: Page, url: str) -> List[str]:
        """Scrape all pages from a single URL"""
        html_pages = []
        
        # Initial page load
        logger.info(f"Loading initial page from {url}")
        page.goto(url, wait_until='networkidle')
        
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
            
            # Wait for network requests to complete (if any)
            page.wait_for_load_state('networkidle')
            
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
        """Scrape data from multiple URLs using single browser instance"""
        if urls is None:
            urls = [self.config.full_url]
            
        results = {}
        browser, page = self._setup_browser()
        
        try:
            for url in urls:
                logger.info(f"Starting to scrape {url}")
                html_pages = self._scrape_single_url(page, url)
                if not html_pages:
                    logger.error(f"Critical error: No pages scraped from {url}")
                    raise RuntimeError(f"No data scraped from {url} - operation cannot continue")
                results[url] = html_pages
                logger.info(f"Successfully scraped {len(results[url])} pages from {url}")
        finally:
            browser.close()
                
        return results
    
    
    def run(self, urls: List[str] = None) -> Dict[str, List[str]]:
        """Main method to run the scraping process and return HTML data"""
        scraped_data = self.scrape_data(urls)
        
        # Verify we have data before returning
        if not scraped_data or all(not pages for pages in scraped_data.values()):
            logger.error("Critical error: No data scraped from any URL")
            raise RuntimeError("No data scraped - operation failed")
        
        logger.info("Scraping process completed successfully")
        return scraped_data
