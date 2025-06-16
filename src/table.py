from dataclasses import dataclass, field
from typing import List, Optional
import logging
import pandas as pd
import cn2an


logger = logging.getLogger(__name__)


@dataclass
class Table:
    """基础表格数据容器"""
    data: pd.DataFrame = field(default_factory=pd.DataFrame)
    name: Optional[str] = None
    source: Optional[str] = None
    
    def insert_column(self, loc: int, column: str, value, allow_duplicates: bool = False):
        """在指定位置插入列"""
        self.data.insert(loc, column, value, allow_duplicates)

    def append_page_data(self, page_data: pd.DataFrame):
        """追加页面数据到表格"""
        # Convert Chinese numbers to pure numbers
        page_data = self._convert_chinese_numbers(page_data)
        
        # Append the new data
        self.data = pd.concat([self.data, page_data], ignore_index=True)
    
    def remove_first_column(self):
        """移除第一列"""
        if not self.data.empty and self.data.shape[1] > 0:
            self.data = self.data.iloc[:, 1:]
    
    def is_empty(self) -> bool:
        """检查表格是否为空"""
        return self.data.empty
    
    def split_and_load_data(self, combined_df: pd.DataFrame, html_content: str, split_row_selector: Optional[str]):
        """Split combined dataframe by selector and load sections into table"""
        sections = self._split_dataframe_by_selector(combined_df, html_content, split_row_selector)
        
        for section in sections:
            self.append_page_data(section)
    
    def _split_dataframe_by_selector(self, df: pd.DataFrame, html_content: str, split_row_selector: Optional[str]) -> List[pd.DataFrame]:
        """Split dataframe by TD selector"""
        if not split_row_selector:
            # No selector provided, return whole dataframe
            return [df]
            
        # Use TD selector method
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "lxml")
        split_tds = soup.select(split_row_selector)
        
        if not split_tds:
            # No matching TDs found, raise exception
            logger.error(f"Critical error: No elements found with selector '{split_row_selector}'")
            raise RuntimeError(f"Split row selector '{split_row_selector}' found no matching elements in HTML")
            
        # Find corresponding row indices by matching TD content
        split_indices = []
        for td in split_tds:
            td_text = td.get_text(strip=True)
            # Find rows in dataframe that contain this TD text in first column
            first_col = df.iloc[:, 0].astype(str)
            matching_rows = first_col.str.contains(td_text, regex=False, na=False)
            if matching_rows.any():
                split_indices.extend(df.index[matching_rows].tolist())
        
        if not split_indices:
            # No matching rows found, raise exception
            logger.error(f"Critical error: Elements found with selector '{split_row_selector}' but no matching rows in dataframe")
            raise RuntimeError(f"Split row selector '{split_row_selector}' found elements but no matching rows in table data")
            
        split_indices = sorted(list(set(split_indices)))  # Remove duplicates and sort
        
        split_dfs = []
        for i, start_idx in enumerate(split_indices):
            if i < len(split_indices) - 1:
                end_idx = split_indices[i + 1]
                section_df = df.iloc[start_idx:end_idx].copy()
            else:
                section_df = df.iloc[start_idx:].copy()
            split_dfs.append(section_df)
        
        logger.info(f"Split dataframe into {len(split_dfs)} sections using TD selector")
        return split_dfs

    def _convert_chinese_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert Chinese number formats to pure numbers using cn2an"""
        # Process data starting from row 1, column 2 (inclusive)
        converted_df = df.copy()
        
        for row_idx in range(0, len(df)):  # Start from row 1 (index 0)
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
                
                # If all conversion attempts failed, keep original value
                if converted_value is None:
                    logger.warning(f"Could not convert number '{cell_str}' at row {row_idx+1}, col {col_idx+1}, keeping original value")
                    converted_df.iloc[row_idx, col_idx] = cell_value
                else:
                    # Apply the converted value
                    converted_df.iloc[row_idx, col_idx] = converted_value
        
        return converted_df


@dataclass
class FinancialTable:
    """金融数据表格容器，由多个Table组成"""
    tables: List[Table] = field(default_factory=list)
    title: Optional[str] = None
    stock_code: Optional[str] = None
    
    def add_table(self, table: Table):
        """添加表格"""
        self.tables.append(table)
    
    def get_combined_dataframe(self) -> pd.DataFrame:
        """获取所有表格合并后的DataFrame"""
        if not self.tables:
            return pd.DataFrame()
        
        table_dataframes = [table.data for table in self.tables]
        combined_df = pd.concat(table_dataframes, axis=0, ignore_index=True)
        
        # Add Title identifier column
        if not combined_df.empty:
            combined_df.insert(0, 'Title', self.title)
        
        return combined_df
    
    def is_empty(self) -> bool:
        """检查是否包含任何表格"""
        return len(self.tables) == 0
