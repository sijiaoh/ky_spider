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
        
        # TODO: 没有title时抛异常
        title = soup.select_one("title")
        page_title = title.text.strip() if title else f"Unknown_Page_{page_index}"
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
                
                try:
                    # TODO: 在cn2an处理失败后尝试处理万亿
                    #
                    # Handle 万亿 directly (cn2an doesn't support it)
                    if '万亿' in cell_str:
                        base_part = cell_str.replace('万亿', '')
                        base_num = float(base_part)
                        converted_value = base_num * 1000000000000  # 1万亿 = 10^12
                        converted_df.iloc[row_idx, col_idx] = converted_value
                    else:
                        # Use cn2an for other Chinese number formats
                        converted_value = cn2an.cn2an(cell_str, "smart")
                        converted_df.iloc[row_idx, col_idx] = converted_value
                except (ValueError, TypeError):
                    # If conversion fails, keep original value
                    continue
        
        return converted_df
    
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
        
        # Combine all URLs vertically
        if not all_url_data:
            logger.error("Critical error: No data from any URL")
            raise RuntimeError("No data available from any URL")
        
        final_df = pd.concat(all_url_data, axis=0, ignore_index=True)
        
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
