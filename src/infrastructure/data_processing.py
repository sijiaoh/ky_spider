import logging
from typing import List
from io import StringIO
import pandas as pd
from bs4 import BeautifulSoup

from ..domain.services import DataProcessingService, ChineseNumberConverter, DataValidator
from ..domain.entities import FinancialData, FinancialDataset
from ..domain.exceptions import DataProcessingException, DataIntegrityException, ValidationException


logger = logging.getLogger(__name__)


class BeautifulSoupDataProcessor(DataProcessingService):
    """BeautifulSoup implementation of data processing service"""
    
    def __init__(self, chinese_converter: ChineseNumberConverter, validator: DataValidator):
        self.chinese_converter = chinese_converter
        self.validator = validator
    
    def extract_financial_data(self, html_content: str, page_index: int, source_url: str) -> FinancialData:
        """Extract financial data from HTML content"""
        try:
            soup = BeautifulSoup(html_content, "lxml")
            
            # Extract title
            title_element = soup.select_one("title")
            title = title_element.text.strip() if title_element else f"Unknown_Page_{page_index}"
            logger.info(f"Processing page {page_index}: {title}")
            
            # Extract table
            table_element = soup.select_one(".zyzb_table .report_table .table1")
            if not table_element:
                raise DataIntegrityException(f"No table found on page {page_index}")
            
            # Convert to DataFrame first for easier processing
            df = pd.read_html(StringIO(str(table_element)))[0]
            
            if df.empty:
                raise DataIntegrityException(f"Empty table data on page {page_index}")
            
            # Remove first column for non-first pages to avoid duplication
            if page_index > 0:
                df = df.iloc[:, 1:]
            
            # Convert DataFrame to list of lists
            data = df.values.tolist()
            
            return FinancialData(
                title=title,
                data=data,
                source_url=source_url,
                page_index=page_index
            )
            
        except Exception as e:
            logger.error(f"Failed to extract data from page {page_index}: {e}")
            raise DataProcessingException(f"Data extraction failed for page {page_index}") from e
    
    def process_dataset(self, dataset: FinancialDataset) -> pd.DataFrame:
        """Process financial dataset into DataFrame"""
        self.validator.validate_dataset(dataset)
        
        try:
            # Combine all pages horizontally
            page_dfs = []
            for page in dataset.pages:
                df = pd.DataFrame(page.data)
                page_dfs.append(df)
            
            combined_df = pd.concat(page_dfs, axis=1, ignore_index=True)
            
            # Split by indicator sections and process each
            indicator_sections = self._split_by_indicators(combined_df)
            
            # Convert Chinese numbers in each section
            converted_sections = []
            for section in indicator_sections:
                converted_section = self.chinese_converter.convert_dataframe(section)
                converted_sections.append(converted_section)
            
            # Recombine sections
            final_df = pd.concat(converted_sections, axis=0, ignore_index=True)
            
            # Add title column
            final_df.insert(0, 'Title', dataset.title)
            
            self.validator.validate_dataframe(final_df)
            
            return final_df
            
        except Exception as e:
            logger.error(f"Failed to process dataset for {dataset.stock_code.value}: {e}")
            raise DataProcessingException(f"Dataset processing failed") from e
    
    def combine_datasets(self, datasets: List[FinancialDataset]) -> pd.DataFrame:
        """Combine multiple datasets into single DataFrame"""
        if not datasets:
            raise ValidationException("No datasets provided")
        
        try:
            processed_dfs = []
            for dataset in datasets:
                df = self.process_dataset(dataset)
                processed_dfs.append(df)
            
            # Combine all datasets vertically
            final_df = pd.concat(processed_dfs, axis=0, ignore_index=True)
            
            self.validator.validate_dataframe(final_df)
            
            logger.info(f"Combined {len(datasets)} datasets into final DataFrame")
            return final_df
            
        except Exception as e:
            logger.error(f"Failed to combine datasets: {e}")
            raise DataProcessingException("Dataset combination failed") from e
    
    def _split_by_indicators(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """Split dataframe by rows where first column ends with 指标"""
        # Find rows where first column ends with 指标
        first_col = df.iloc[:, 0].astype(str)
        indicator_rows = first_col.str.endswith('指标')
        indicator_indices = df.index[indicator_rows].tolist()
        
        if not indicator_indices:
            return [df]
        
        indicator_dfs = []
        
        for i, start_idx in enumerate(indicator_indices):
            if i < len(indicator_indices) - 1:
                end_idx = indicator_indices[i + 1]
                section_df = df.iloc[start_idx:end_idx].copy()
            else:
                section_df = df.iloc[start_idx:].copy()
            
            indicator_dfs.append(section_df)
        
        logger.info(f"Split dataframe into {len(indicator_dfs)} indicator sections")
        return indicator_dfs