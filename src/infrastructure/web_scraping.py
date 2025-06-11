import logging
from typing import List
from playwright.sync_api import sync_playwright, Browser, Page

from ..domain.repositories import WebScrapingRepository
from ..domain.exceptions import ScrapingException, DataIntegrityException


logger = logging.getLogger(__name__)


class PlaywrightWebScrapingRepository(WebScrapingRepository):
    """Playwright implementation of web scraping repository"""
    
    def __init__(self, headless: bool = True, timeout: int = 10000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser = None
    
    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
    
    def scrape_financial_data(self, url: str) -> List[str]:
        """Scrape HTML pages from a financial data URL"""
        if not self._browser:
            raise ScrapingException("Browser not initialized. Use context manager.")
        
        page = self._browser.new_page()
        page.set_default_timeout(self.timeout)
        
        try:
            return self._scrape_all_pages(page, url)
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            raise ScrapingException(f"Scraping failed for {url}") from e
        finally:
            page.close()
    
    def _scrape_all_pages(self, page: Page, url: str) -> List[str]:
        """Scrape all pages from a single URL"""
        html_pages = []
        
        logger.info(f"Loading initial page from {url}")
        page.goto(url)
        
        # Wait for table to be fully loaded
        logger.info("Waiting for table to load...")
        page.wait_for_selector(".zyzb_table .report_table .table1", timeout=self.timeout)
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
                raise DataIntegrityException("Table disappeared during pagination")
                
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
                timeout=self.timeout
            )
            page_count += 1
            
        if not html_pages:
            raise DataIntegrityException(f"No pages scraped from {url}")
            
        return html_pages