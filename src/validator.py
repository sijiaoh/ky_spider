"""
Data validation framework for ensuring data integrity and accuracy.
All validation failures result in immediate termination.
"""

import logging
import pandas as pd
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class DataIntegrityError(Exception):
    """Critical data integrity violation that requires immediate termination"""
    pass


class TableStructureError(DataIntegrityError):
    """Table structure does not match expected format"""
    pass


class DataContentError(DataIntegrityError):
    """Data content validation failed"""
    pass


class DataValidator:
    """Strict data validation with immediate failure on any violation"""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        
    def validate_dataframe_not_empty(self, df: pd.DataFrame, context: str) -> None:
        """Validate DataFrame is not empty - CRITICAL"""
        if df is None:
            raise DataIntegrityError(f"Critical failure: DataFrame is None in {context}")
        
        if df.empty:
            raise DataIntegrityError(f"Critical failure: Empty DataFrame in {context}")
        
        logger.debug(f"✓ DataFrame not empty: {df.shape} in {context}")
    
    def validate_minimum_dimensions(self, df: pd.DataFrame, min_rows: int, min_cols: int, context: str) -> None:
        """Validate DataFrame meets minimum size requirements - CRITICAL"""
        if df.shape[0] < min_rows:
            raise TableStructureError(
                f"Critical failure: Insufficient rows {df.shape[0]} < {min_rows} in {context}"
            )
        
        if df.shape[1] < min_cols:
            raise TableStructureError(
                f"Critical failure: Insufficient columns {df.shape[1]} < {min_cols} in {context}"
            )
        
        logger.debug(f"✓ Minimum dimensions met: {df.shape} >= ({min_rows}, {min_cols}) in {context}")
    
    def validate_expected_dimensions(self, df: pd.DataFrame, expected_rows: int, expected_cols: int, context: str) -> None:
        """Validate DataFrame matches exact expected dimensions - CRITICAL"""
        if df.shape != (expected_rows, expected_cols):
            raise TableStructureError(
                f"Critical failure: Dimension mismatch {df.shape} != ({expected_rows}, {expected_cols}) in {context}"
            )
        
        logger.debug(f"✓ Expected dimensions match: {df.shape} in {context}")
    
    def validate_no_all_nan_rows(self, df: pd.DataFrame, context: str) -> None:
        """Validate no rows are completely empty - CRITICAL"""
        all_nan_rows = df.isnull().all(axis=1).sum()
        if all_nan_rows > 0:
            raise DataContentError(
                f"Critical failure: {all_nan_rows} completely empty rows found in {context}"
            )
        
        logger.debug(f"✓ No completely empty rows in {context}")
    
    def validate_no_all_nan_columns(self, df: pd.DataFrame, context: str) -> None:
        """Validate no columns are completely empty - CRITICAL"""
        all_nan_cols = df.isnull().all(axis=0).sum()
        if all_nan_cols > 0:
            raise DataContentError(
                f"Critical failure: {all_nan_cols} completely empty columns found in {context}"
            )
        
        logger.debug(f"✓ No completely empty columns in {context}")
    
    def validate_indicator_markers_present(self, df: pd.DataFrame, context: str) -> None:
        """Validate that indicator markers (ending with '指标') are present - CRITICAL"""
        if df.empty or df.shape[1] == 0:
            raise DataIntegrityError(f"Critical failure: Cannot validate indicators in empty DataFrame in {context}")
        
        first_col = df.iloc[:, 0].astype(str)
        indicator_count = first_col.str.endswith('指标').sum()
        
        if indicator_count == 0:
            raise DataContentError(
                f"Critical failure: No indicator markers found in first column in {context}"
            )
        
        logger.debug(f"✓ Found {indicator_count} indicator markers in {context}")
    
    def validate_numeric_data_region(self, df: pd.DataFrame, start_row: int, start_col: int, context: str) -> None:
        """Validate that data region contains processable content - CRITICAL"""
        if df.shape[0] <= start_row or df.shape[1] <= start_col:
            raise TableStructureError(
                f"Critical failure: DataFrame too small for data region starting at ({start_row}, {start_col}) in {context}"
            )
        
        data_region = df.iloc[start_row:, start_col:]
        non_null_count = data_region.count().sum()
        
        if non_null_count == 0:
            raise DataContentError(
                f"Critical failure: No data found in numeric region starting at ({start_row}, {start_col}) in {context}"
            )
        
        logger.debug(f"✓ Found {non_null_count} non-null values in data region in {context}")
    
    def validate_page_extraction_success(self, html_content: str, page_index: int) -> None:
        """Validate successful page content extraction - CRITICAL"""
        if not html_content or len(html_content.strip()) == 0:
            raise DataIntegrityError(f"Critical failure: Empty HTML content for page {page_index}")
        
        if len(html_content) < 100:  # Suspiciously short content
            raise DataIntegrityError(f"Critical failure: Suspiciously short HTML content ({len(html_content)} chars) for page {page_index}")
        
        logger.debug(f"✓ Valid HTML content extracted for page {page_index}: {len(html_content)} characters")
    
    def validate_table_extraction_success(self, df: pd.DataFrame, page_index: int) -> None:
        """Validate successful table extraction from HTML - CRITICAL"""
        if df is None:
            raise DataIntegrityError(f"Critical failure: No table extracted from page {page_index}")
        
        self.validate_dataframe_not_empty(df, f"page {page_index} table extraction")
        self.validate_minimum_dimensions(df, min_rows=2, min_cols=2, context=f"page {page_index}")
        
        logger.debug(f"✓ Valid table extracted from page {page_index}: {df.shape}")
    
    def validate_pagination_integrity(self, total_pages: int, expected_min_pages: int = 1) -> None:
        """Validate pagination extracted expected number of pages - CRITICAL"""
        if total_pages < expected_min_pages:
            raise DataIntegrityError(
                f"Critical failure: Insufficient pages extracted {total_pages} < {expected_min_pages}"
            )
        
        if total_pages > 1000:  # Sanity check for runaway pagination
            raise DataIntegrityError(
                f"Critical failure: Suspiciously high page count {total_pages} - possible infinite loop"
            )
        
        logger.debug(f"✓ Valid pagination: {total_pages} pages extracted")
    
    def validate_url_data_consistency(self, url_data: Dict[str, List[str]], min_urls: int = 1) -> None:
        """Validate consistency across multiple URL extractions - CRITICAL"""
        if len(url_data) < min_urls:
            raise DataIntegrityError(f"Critical failure: Insufficient URLs processed {len(url_data)} < {min_urls}")
        
        for url, pages in url_data.items():
            if not pages:
                raise DataIntegrityError(f"Critical failure: No pages extracted for URL {url}")
            
            for i, page_content in enumerate(pages):
                self.validate_page_extraction_success(page_content, i)
        
        logger.debug(f"✓ Valid data from {len(url_data)} URLs")
    
    def validate_final_output(self, df: pd.DataFrame, expected_features: Optional[Dict[str, Any]] = None) -> None:
        """Final validation before output - CRITICAL"""
        self.validate_dataframe_not_empty(df, "final output")
        
        # Validate basic structure
        if df.shape[1] < 2:  # Must have at least Title column + data
            raise DataIntegrityError(f"Critical failure: Final output has insufficient columns: {df.shape[1]}")
        
        # Validate Title column exists and is not empty
        if 'Title' not in df.columns and df.columns[0] != 'Title':
            # Check if first column could be title
            first_col_name = df.columns[0] if len(df.columns) > 0 else 'Unknown'
            logger.warning(f"Title column not found, using first column: {first_col_name}")
        
        # Check for completely empty rows in final output
        self.validate_no_all_nan_rows(df, "final output")
        
        if expected_features:
            if 'min_rows' in expected_features:
                self.validate_minimum_dimensions(df, expected_features['min_rows'], 1, "final output")
            
            if 'expected_columns' in expected_features:
                if df.shape[1] != expected_features['expected_columns']:
                    raise TableStructureError(
                        f"Critical failure: Column count mismatch {df.shape[1]} != {expected_features['expected_columns']}"
                    )
        
        logger.info(f"✓ Final validation passed: {df.shape}")