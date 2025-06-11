import logging
from typing import List
from pathlib import Path

from ..domain.entities import StockCode, ScrapingTarget, FinancialDataset, ExportRequest
from ..domain.repositories import WebScrapingRepository, DataExportRepository
from ..domain.services import DataProcessingService
from ..domain.exceptions import ScrapingException, DataIntegrityException, ExportException


logger = logging.getLogger(__name__)


class ScrapeFinancialDataUseCase:
    """Use case for scraping financial data"""
    
    def __init__(
        self,
        web_scraping_repo: WebScrapingRepository,
        data_processor: DataProcessingService
    ):
        self.web_scraping_repo = web_scraping_repo
        self.data_processor = data_processor
    
    def execute(self, targets: List[ScrapingTarget]) -> List[FinancialDataset]:
        """Execute the scraping use case"""
        if not targets:
            raise ScrapingException("No scraping targets provided")
        
        datasets = []
        
        for target in targets:
            logger.info(f"Scraping data for {target.stock_code.value}")
            
            try:
                # Scrape HTML pages
                html_pages = self.web_scraping_repo.scrape_financial_data(target.url)
                
                if not html_pages:
                    raise DataIntegrityException(f"No data scraped for {target.stock_code.value}")
                
                # Process each page
                financial_pages = []
                title = None
                
                for i, html_content in enumerate(html_pages):
                    page_data = self.data_processor.extract_financial_data(
                        html_content, i, target.url
                    )
                    financial_pages.append(page_data)
                    
                    # Use first page title as dataset title
                    if title is None:
                        title = page_data.title
                
                # Create dataset
                dataset = FinancialDataset(
                    stock_code=target.stock_code,
                    title=title or f"Dataset_{target.stock_code.value}",
                    pages=financial_pages
                )
                
                datasets.append(dataset)
                logger.info(f"Successfully scraped {len(html_pages)} pages for {target.stock_code.value}")
                
            except Exception as e:
                logger.error(f"Failed to scrape {target.stock_code.value}: {e}")
                raise ScrapingException(f"Scraping failed for {target.stock_code.value}") from e
        
        return datasets


class ExportFinancialDataUseCase:
    """Use case for exporting financial data"""
    
    def __init__(self, data_export_repo: DataExportRepository):
        self.data_export_repo = data_export_repo
    
    def execute(self, datasets: List[FinancialDataset], output_path: Path) -> None:
        """Execute the export use case"""
        if not datasets:
            raise ExportException("No datasets to export")
        
        try:
            export_request = ExportRequest(datasets=datasets, output_path=output_path)
            
            # Determine export format based on file extension
            if output_path.suffix.lower() == '.xlsx':
                self.data_export_repo.export_to_excel(export_request)
            elif output_path.suffix.lower() == '.csv':
                self.data_export_repo.export_to_csv(export_request)
            else:
                raise ExportException(f"Unsupported export format: {output_path.suffix}")
            
            logger.info(f"Successfully exported {len(datasets)} datasets to {output_path}")
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise ExportException("Export operation failed") from e


class ScrapingWorkflow:
    """Complete scraping workflow orchestrator"""
    
    def __init__(
        self,
        scrape_use_case: ScrapeFinancialDataUseCase,
        export_use_case: ExportFinancialDataUseCase
    ):
        self.scrape_use_case = scrape_use_case
        self.export_use_case = export_use_case
    
    def execute(self, targets: List[ScrapingTarget], output_path: Path) -> None:
        """Execute complete scraping workflow"""
        logger.info(f"Starting scraping workflow for {len(targets)} targets")
        
        try:
            # Scrape data
            datasets = self.scrape_use_case.execute(targets)
            
            # Export data
            self.export_use_case.execute(datasets, output_path)
            
            logger.info("Scraping workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Scraping workflow failed: {e}")
            raise