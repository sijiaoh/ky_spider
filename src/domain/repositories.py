from abc import ABC, abstractmethod
from typing import List, Protocol
from pathlib import Path

from .entities import FinancialDataset, ExportRequest


class WebScrapingRepository(ABC):
    """Abstract repository for web scraping operations"""
    
    @abstractmethod
    def scrape_financial_data(self, url: str) -> List[str]:
        """Scrape HTML pages from a financial data URL"""
        pass


class DataExportRepository(ABC):
    """Abstract repository for data export operations"""
    
    @abstractmethod
    def export_to_excel(self, export_request: ExportRequest) -> None:
        """Export financial datasets to Excel file"""
        pass
    
    @abstractmethod
    def export_to_csv(self, export_request: ExportRequest) -> None:
        """Export financial datasets to CSV file"""
        pass


class FileSystemRepository(ABC):
    """Abstract repository for file system operations"""
    
    @abstractmethod
    def ensure_directory_exists(self, path: Path) -> None:
        """Ensure directory exists"""
        pass
    
    @abstractmethod
    def verify_file_created(self, path: Path) -> bool:
        """Verify file was created and has content"""
        pass