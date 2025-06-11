import logging
from typing import Union
import pandas as pd
import cn2an

from ..domain.services import ChineseNumberConverter
from ..domain.exceptions import DataProcessingException


logger = logging.getLogger(__name__)


class Cn2anChineseConverter(ChineseNumberConverter):
    """cn2an implementation of Chinese number converter"""
    
    def convert_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert Chinese numbers in DataFrame to numeric values"""
        if df.empty:
            return df
        
        try:
            converted_df = df.copy()
            
            # Process data starting from row 2, column 2 (inclusive)
            for row_idx in range(1, len(df)):  # Start from row 2 (index 1)
                for col_idx in range(1, len(df.columns)):  # Start from column 2 (index 1)
                    cell_value = df.iloc[row_idx, col_idx]
                    
                    if pd.isna(cell_value):
                        continue
                    
                    cell_str = str(cell_value).strip()
                    if not cell_str:
                        continue
                    
                    try:
                        converted_value = self.convert_value(cell_str)
                        converted_df.iloc[row_idx, col_idx] = converted_value
                    except (ValueError, TypeError):
                        # If conversion fails, keep original value
                        continue
            
            return converted_df
            
        except Exception as e:
            logger.error(f"Failed to convert Chinese numbers in DataFrame: {e}")
            raise DataProcessingException("Chinese number conversion failed") from e
    
    def convert_value(self, value: str) -> Union[float, str]:
        """Convert single Chinese number to numeric value"""
        try:
            # Handle 万亿 directly (cn2an doesn't support it well)
            if '万亿' in value:
                base_part = value.replace('万亿', '')
                base_num = float(base_part)
                return base_num * 1000000000000  # 1万亿 = 10^12
            else:
                # Use cn2an for other Chinese number formats
                return cn2an.cn2an(value, "smart")
        except (ValueError, TypeError):
            # If conversion fails, return original value
            return value