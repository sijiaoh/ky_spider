from abc import ABC, abstractmethod
from typing import List
import pandas as pd

from .entities import FinancialData, FinancialDataset


class DataProcessingService(ABC):
    """Abstract service for data processing operations"""
    
    @abstractmethod
    def extract_financial_data(self, html_content: str, page_index: int, source_url: str) -> FinancialData:
        """Extract financial data from HTML content"""
        pass
    
    @abstractmethod
    def process_dataset(self, dataset: FinancialDataset) -> pd.DataFrame:
        """Process financial dataset into DataFrame"""
        pass
    
    @abstractmethod
    def combine_datasets(self, datasets: List[FinancialDataset]) -> pd.DataFrame:
        """Combine multiple datasets into single DataFrame"""
        pass


class ChineseNumberConverter(ABC):
    """Abstract service for Chinese number conversion"""
    
    @abstractmethod
    def convert_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert Chinese numbers in DataFrame to numeric values"""
        pass
    
    @abstractmethod
    def convert_value(self, value: str) -> float:
        """Convert single Chinese number to numeric value"""
        pass


class DataValidator(ABC):
    """Abstract service for data validation"""
    
    @abstractmethod
    def validate_dataset(self, dataset: FinancialDataset) -> None:
        """Validate financial dataset"""
        pass
    
    @abstractmethod
    def validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate DataFrame content"""
        pass