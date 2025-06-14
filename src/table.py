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


@dataclass
class FinancialTable:
    """金融数据表格容器，由多个Table组成"""
    tables: List[Table]
    title: Optional[str] = None
    stock_code: Optional[str] = None
    
    def __post_init__(self):
        if self.tables is None:
            self.tables = []