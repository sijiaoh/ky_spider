import logging
import pandas as pd

from ..domain.services import DataValidator
from ..domain.entities import FinancialDataset
from ..domain.exceptions import ValidationException, DataIntegrityException


logger = logging.getLogger(__name__)


class StrictDataValidator(DataValidator):
    """Strict implementation of data validator"""
    
    def validate_dataset(self, dataset: FinancialDataset) -> None:
        """Validate financial dataset"""
        if not dataset:
            raise ValidationException("Dataset is None")
        
        if not dataset.stock_code:
            raise ValidationException("Dataset must have stock code")
        
        if dataset.is_empty():
            raise DataIntegrityException(f"Dataset for {dataset.stock_code.value} is empty")
        
        if not dataset.pages:
            raise DataIntegrityException(f"Dataset for {dataset.stock_code.value} has no pages")
        
        # Validate each page
        for i, page in enumerate(dataset.pages):
            if page.is_empty():
                raise DataIntegrityException(f"Page {i} in dataset {dataset.stock_code.value} is empty")
            
            if not page.title or not page.title.strip():
                raise ValidationException(f"Page {i} in dataset {dataset.stock_code.value} has no title")
        
        logger.info(f"Dataset validation passed for {dataset.stock_code.value}")
    
    def validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate DataFrame content"""
        if df is None:
            raise ValidationException("DataFrame is None")
        
        if df.empty:
            raise DataIntegrityException("DataFrame is empty")
        
        if len(df.columns) == 0:
            raise DataIntegrityException("DataFrame has no columns")
        
        if len(df.index) == 0:
            raise DataIntegrityException("DataFrame has no rows")
        
        logger.info(f"DataFrame validation passed: {df.shape[0]} rows, {df.shape[1]} columns")