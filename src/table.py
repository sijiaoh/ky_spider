from dataclasses import dataclass
from typing import List, Optional
import pandas as pd


@dataclass
class Table:
    """基础表格数据容器"""
    data: pd.DataFrame
    name: Optional[str] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = pd.DataFrame()
    
    def insert_column(self, loc: int, column: str, value, allow_duplicates: bool = False):
        """在指定位置插入列"""
        self.data.insert(loc, column, value, allow_duplicates)
    
    def remove_first_column(self):
        """移除第一列"""
        if not self.data.empty and self.data.shape[1] > 0:
            self.data = self.data.iloc[:, 1:]
    
    def is_empty(self) -> bool:
        """检查表格是否为空"""
        return self.data.empty


@dataclass
class FinancialTable:
    """金融数据表格容器，由多个Table组成"""
    tables: List[Table]
    title: Optional[str] = None
    stock_code: Optional[str] = None
    
    def __post_init__(self):
        if self.tables is None:
            self.tables = []
    
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