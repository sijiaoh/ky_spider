import logging
from typing import List, Dict
from pathlib import Path

from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO
import cn2an

from .config import ScrapingConfig


logger = logging.getLogger(__name__)


class FinancialDataProcessor:
    """Processor for financial data HTML content"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        
    def _extract_page_data(self, html_content: str, page_index: int) -> tuple[pd.DataFrame, str]:
        """Extract table data and title from HTML content"""
        soup = BeautifulSoup(html_content, "lxml")
        
        title = soup.select_one("title")
        if not title or not title.text.strip():
            logger.error(f"Critical error: No title found on page {page_index}")
            raise RuntimeError(f"Page title not found on page {page_index} - data integrity compromised")
        
        page_title = title.text.strip()
        logger.info(f"Processing page {page_index}: {page_title}")
        
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
        
        return df, page_title
    
    def _split_dataframe_by_indicators(self, df: pd.DataFrame) -> List[pd.DataFrame]:
        """Split dataframe by rows where first column ends with 指标"""
        # Find rows where first column ends with 指标
        first_col = df.iloc[:, 0].astype(str)
        indicator_rows = first_col.str.endswith('指标')
        indicator_indices = df.index[indicator_rows].tolist()
        
        if not indicator_indices:
            # No indicator sections found, return whole dataframe
            return [df]
        
        indicator_dfs = []
        
        for i, start_idx in enumerate(indicator_indices):
            if i < len(indicator_indices) - 1:
                # Section from current indicator to next indicator (exclusive)
                end_idx = indicator_indices[i + 1]
                section_df = df.iloc[start_idx:end_idx].copy()
            else:
                # Last section: from current indicator to end of dataframe
                section_df = df.iloc[start_idx:].copy()
            
            indicator_dfs.append(section_df)
        
        logger.info(f"Split dataframe into {len(indicator_dfs)} indicator sections")
        return indicator_dfs
    
    def _convert_chinese_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert Chinese number formats to pure numbers using cn2an"""
        # Process data starting from row 2, column 2 (inclusive)
        converted_df = df.copy()
        
        for row_idx in range(1, len(df)):  # Start from row 2 (index 1)
            for col_idx in range(1, len(df.columns)):  # Start from column 2 (index 1)
                cell_value = df.iloc[row_idx, col_idx]
                
                if pd.isna(cell_value):
                    continue
                
                cell_str = str(cell_value).strip()
                if not cell_str:
                    continue
                
                # Skip non-data indicators
                if cell_str == "--":
                    continue
                
                converted_value = None
                
                # Try cn2an first for standard Chinese number formats
                try:
                    converted_value = cn2an.cn2an(cell_str, "smart")
                except (ValueError, TypeError):
                    # If cn2an fails, try handling 万亿 directly
                    if '万亿' in cell_str:
                        try:
                            base_part = cell_str.replace('万亿', '')
                            base_num = float(base_part)
                            converted_value = base_num * 1000000000000  # 1万亿 = 10^12
                        except (ValueError, TypeError):
                            pass  # Will be handled below
                
                # If all conversion attempts failed, raise exception
                if converted_value is None:
                    logger.error(f"Critical error: Failed to convert number '{cell_str}' at row {row_idx+1}, col {col_idx+1}")
                    raise RuntimeError(f"Number conversion failed for '{cell_str}' - data integrity compromised")
                
                # Apply the converted value
                converted_df.iloc[row_idx, col_idx] = converted_value
        
        return converted_df
    
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
    
    def process_and_save_data(self, scraped_data: Dict[str, List[str]]) -> None:
        """Process scraped HTML data and save to Excel"""
        self.config.output_dir.mkdir(exist_ok=True)
        
        all_url_data = []
        
        # Process each URL's data
        for url, html_pages in scraped_data.items():
            if not html_pages:
                logger.error(f"Critical error: No data to process for {url}")
                raise RuntimeError(f"No data available for processing from {url}")
            
            logger.info(f"Processing data from {url}")
            page_tables = []
            
            # Process each page within the URL
            page_title = None
            for i, html_content in enumerate(html_pages):
                df, title = self._extract_page_data(html_content, i)
                if page_title is None:
                    page_title = title
                page_tables.append(df)
            
            # Combine pages horizontally for this URL
            url_combined_df = pd.concat(page_tables, axis=1, ignore_index=True)
            
            # Split the URL's combined data by indicator sections
            indicator_sections = self._split_dataframe_by_indicators(url_combined_df)
            
            # Convert Chinese numbers in each section
            converted_sections = []
            for section in indicator_sections:
                converted_section = self._convert_chinese_numbers(section)
                converted_sections.append(converted_section)
            
            # Recombine the converted indicator sections for this URL
            url_combined_df = pd.concat(converted_sections, axis=0, ignore_index=True)
            
            if url_combined_df.empty:
                logger.error(f"Critical error: Combined dataframe is empty for {url}")
                raise RuntimeError(f"Final dataframe is empty for {url}")
            
            # Add Title identifier column instead of URL
            url_combined_df.insert(0, 'Title', page_title)
            all_url_data.append(url_combined_df)
            logger.info(f"Processed {len(page_tables)} pages from {url} with title: {page_title}")
        
        # Combine all URLs with date alignment
        if not all_url_data:
            logger.error("Critical error: No data from any URL")
            raise RuntimeError("No data available from any URL")
        
        final_df = self._merge_by_date_alignment(all_url_data)
        
        if final_df.empty:
            logger.error("Critical error: Final combined dataframe is empty")
            raise RuntimeError("Final combined dataframe is empty")
        
        # Save to Excel
        final_df.to_excel(self.config.output_path, index=False)
        logger.info(f"Combined data from {len(scraped_data)} URLs saved to {self.config.output_path}")
        
        # Verify file was created and has content
        if not self.config.output_path.exists():
            logger.error(f"Critical error: Output file not created: {self.config.output_path}")
            raise RuntimeError(f"Failed to create output file: {self.config.output_path}")
        
        if self.config.output_path.stat().st_size == 0:
            logger.error(f"Critical error: Output file is empty: {self.config.output_path}")
            raise RuntimeError(f"Output file is empty: {self.config.output_path}")
