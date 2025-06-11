from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass(frozen=True)
class StockCode:
    """Stock code value object"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Stock code cannot be empty")
        if len(self.value) < 6:
            raise ValueError("Stock code must be at least 6 characters")


@dataclass(frozen=True)
class ScrapingTarget:
    """Represents a scraping target with URL and identifier"""
    stock_code: StockCode
    url: str
    
    @property
    def identifier(self) -> str:
        return self.stock_code.value


@dataclass
class FinancialData:
    """Financial data extracted from a single page"""
    title: str
    data: List[List[str]]
    source_url: str
    page_index: int
    
    def is_empty(self) -> bool:
        return not self.data or all(not row for row in self.data)


@dataclass
class FinancialDataset:
    """Complete financial dataset for a stock"""
    stock_code: StockCode
    title: str
    pages: List[FinancialData]
    
    def is_empty(self) -> bool:
        return not self.pages or all(page.is_empty() for page in self.pages)
    
    @property
    def total_pages(self) -> int:
        return len(self.pages)


@dataclass
class ExportRequest:
    """Request to export data to file"""
    datasets: List[FinancialDataset]
    output_path: Path
    
    def validate(self) -> None:
        if not self.datasets:
            raise ValueError("No datasets to export")
        if not self.output_path:
            raise ValueError("Output path is required")
        if self.output_path.suffix.lower() not in ['.xlsx', '.csv']:
            raise ValueError("Only .xlsx and .csv formats are supported")