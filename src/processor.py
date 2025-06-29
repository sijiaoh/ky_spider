import logging
from typing import List, Dict, Optional
from pathlib import Path

from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import cn2an

from .config import ScrapingConfig, TableConfig
from .table import Table, FinancialTable


logger = logging.getLogger(__name__)


class FinancialDataProcessor:
    """Processor for financial data HTML content"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
    
    def _merge_by_date_alignment(self, url_dataframes: List[pd.DataFrame]) -> pd.DataFrame:
        """Merge dataframes from different URLs by aligning date columns"""
        if len(url_dataframes) == 1:
            return url_dataframes[0]
        
        # Constants for table structure
        TITLE_COL_IDX = 0
        INDICATOR_COL_IDX = 1
        DATE_COLS_START_IDX = 2
        NUM_FIXED_COLS = 2  # Title and indicator columns
        
        # Collect all unique dates from headers (skip empty columns)
        all_dates = set()
        for df in url_dataframes:
            has_date_columns = df.shape[1] > DATE_COLS_START_IDX
            has_rows = df.shape[0] > 0
            if has_date_columns and has_rows:
                date_column_range = range(DATE_COLS_START_IDX, df.shape[1])
                for date_col_idx in date_column_range:
                    date_header_cell = df.iloc[0, date_col_idx]
                    if date_header_cell is not None:
                        date_text = str(date_header_cell).strip()
                        if date_text:  # Only add non-empty date headers
                            all_dates.add(date_text)
        
        # Sort dates in reverse order (newest to oldest, right to left)
        sorted_dates_newest_first = sorted(list(all_dates), reverse=True)
        unique_date_count = len(sorted_dates_newest_first)
        logger.info(f"Found {unique_date_count} unique dates across all URLs")
        
        # Create aligned result dataframe with numeric column indices
        total_columns = NUM_FIXED_COLS + unique_date_count
        result_df = pd.DataFrame(columns=range(total_columns))
        
        # Process each URL's data
        for url_df in url_dataframes:
            # Create mapping from original column index to date value
            original_col_to_date = {}
            has_date_columns = url_df.shape[1] > DATE_COLS_START_IDX
            has_rows = url_df.shape[0] > 0
            
            if has_date_columns and has_rows:
                date_column_range = range(DATE_COLS_START_IDX, url_df.shape[1])
                for original_col_idx in date_column_range:
                    date_header_cell = url_df.iloc[0, original_col_idx]
                    date_text = str(date_header_cell).strip()
                    date_exists_in_final_list = date_text and date_text in sorted_dates_newest_first
                    if date_exists_in_final_list:
                        original_col_to_date[original_col_idx] = date_text
            
            # Add rows from this URL to result
            total_rows = url_df.shape[0]
            for row_idx in range(total_rows):
                new_row_data = [None] * total_columns
                
                # Copy title and indicator columns
                fixed_cols_to_copy = min(NUM_FIXED_COLS, url_df.shape[1])
                for fixed_col_idx in range(fixed_cols_to_copy):
                    new_row_data[fixed_col_idx] = url_df.iloc[row_idx, fixed_col_idx]
                
                # Map date columns to aligned positions
                for original_col_idx, date_value in original_col_to_date.items():
                    column_exists = original_col_idx < url_df.shape[1]
                    if column_exists:
                        position_in_sorted_dates = sorted_dates_newest_first.index(date_value)
                        aligned_result_col_idx = NUM_FIXED_COLS + position_in_sorted_dates
                        cell_value = url_df.iloc[row_idx, original_col_idx]
                        new_row_data[aligned_result_col_idx] = cell_value
                
                # Add row to result dataframe
                current_result_row_count = len(result_df)
                result_df.loc[current_result_row_count] = new_row_data
        
        processed_url_count = len(url_dataframes)
        logger.info(f"Merged {processed_url_count} URL dataframes with date alignment")
        return result_df
    
    def process_and_save_data(self, scraped_data: Dict[str, Dict[str, List[str]]]) -> None:
        """Process scraped HTML data and save to Excel"""
        self.config.output_dir.mkdir(exist_ok=True)
        
        financial_tables = []
        
        # Process each URL's data
        for url, table_data in scraped_data.items():
            if not table_data:
                logger.error(f"Critical error: No data to process for {url}")
                raise RuntimeError(f"No data available for processing from {url}")
            
            logger.info(f"Processing data from {url}")
            url_table_objects = []
            
            # Process each table within the URL
            for table_index, (table_name, html_pages) in enumerate(table_data.items()):
                if not html_pages:
                    logger.warning(f"No pages for table {table_name} in {url}")
                    continue
                
                # Get table config by index (scraper maintains table order)
                table_config = self.config.tables[table_index]
                logger.info(f"Processing table {table_name} from {url}")
                
                # Create Table object and let it handle page merging and data loading
                table = Table(
                    name=table_name,
                    source=url,
                    config=table_config,
                    html_pages=html_pages
                )
                
                # Add table identifier column
                table.insert_column(0, 'Table', table_name)
                url_table_objects.append(table)
                logger.info(f"Processed {len(table.page_dataframes)} pages for table {table_name}")
            
            # Create FinancialTable for this URL
            if url_table_objects:
                # Create FinancialTable object
                financial_table = FinancialTable(
                    tables=url_table_objects,
                    title=table.page_title,
                    stock_code=self.config.stock_code
                )
                financial_tables.append(financial_table)
                logger.info(f"Combined {len(url_table_objects)} tables from {url}")
            else:
                logger.error(f"Critical error: No valid tables processed for {url}")
                raise RuntimeError(f"No valid tables processed for {url}")
        
        # Combine all URLs with date alignment
        if not financial_tables:
            logger.error("Critical error: No data from any URL")
            raise RuntimeError("No data available from any URL")
        
        # Extract combined dataframes from FinancialTable objects for merging
        url_dataframes = []
        for financial_table in financial_tables:
            url_combined_df = financial_table.get_combined_dataframe()
            
            if url_combined_df.empty:
                logger.error(f"Critical error: Combined dataframe is empty for {financial_table.title}")
                raise RuntimeError(f"Final dataframe is empty for {financial_table.title}")
            
            url_dataframes.append(url_combined_df)
        
        final_df = self._merge_by_date_alignment(url_dataframes)
        
        if final_df.empty:
            logger.error("Critical error: Final combined dataframe is empty")
            raise RuntimeError("Final combined dataframe is empty")
        
        # Save to Excel
        final_df.to_excel(self.config.output_path, index=False)
        logger.info(f"Combined data from {len(financial_tables)} URLs saved to {self.config.output_path}")
        
        # Verify file was created and has content
        if not self.config.output_path.exists():
            logger.error(f"Critical error: Output file not created: {self.config.output_path}")
            raise RuntimeError(f"Failed to create output file: {self.config.output_path}")
        
        if self.config.output_path.stat().st_size == 0:
            logger.error(f"Critical error: Output file is empty: {self.config.output_path}")
            raise RuntimeError(f"Output file is empty: {self.config.output_path}")
