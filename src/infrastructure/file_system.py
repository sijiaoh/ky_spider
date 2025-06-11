import logging
from pathlib import Path
import pandas as pd

from ..domain.repositories import DataExportRepository, FileSystemRepository
from ..domain.entities import ExportRequest
from ..domain.exceptions import ExportException


logger = logging.getLogger(__name__)


class PandasDataExporter(DataExportRepository):
    """Pandas implementation of data export repository"""
    
    def __init__(self, file_system: FileSystemRepository):
        self.file_system = file_system
    
    def export_to_excel(self, export_request: ExportRequest) -> None:
        """Export financial datasets to Excel file"""
        export_request.validate()
        
        try:
            # Ensure output directory exists
            self.file_system.ensure_directory_exists(export_request.output_path.parent)
            
            # Process all datasets into a single DataFrame
            from .data_processing import BeautifulSoupDataProcessor
            from .chinese_converter import Cn2anChineseConverter
            from .validation import StrictDataValidator
            
            # Create processor (this is a bit circular, should be injected)
            converter = Cn2anChineseConverter()
            validator = StrictDataValidator()
            processor = BeautifulSoupDataProcessor(converter, validator)
            
            final_df = processor.combine_datasets(export_request.datasets)
            
            # Export to Excel
            final_df.to_excel(export_request.output_path, index=False)
            
            # Verify file was created
            if not self.file_system.verify_file_created(export_request.output_path):
                raise ExportException(f"Failed to create Excel file: {export_request.output_path}")
            
            logger.info(f"Successfully exported {len(export_request.datasets)} datasets to {export_request.output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export to Excel: {e}")
            raise ExportException(f"Excel export failed") from e
    
    def export_to_csv(self, export_request: ExportRequest) -> None:
        """Export financial datasets to CSV file"""
        export_request.validate()
        
        try:
            # Ensure output directory exists
            self.file_system.ensure_directory_exists(export_request.output_path.parent)
            
            # Process all datasets into a single DataFrame
            from .data_processing import BeautifulSoupDataProcessor
            from .chinese_converter import Cn2anChineseConverter
            from .validation import StrictDataValidator
            
            # Create processor
            converter = Cn2anChineseConverter()
            validator = StrictDataValidator()
            processor = BeautifulSoupDataProcessor(converter, validator)
            
            final_df = processor.combine_datasets(export_request.datasets)
            
            # Export to CSV
            final_df.to_csv(export_request.output_path, index=False)
            
            # Verify file was created
            if not self.file_system.verify_file_created(export_request.output_path):
                raise ExportException(f"Failed to create CSV file: {export_request.output_path}")
            
            logger.info(f"Successfully exported {len(export_request.datasets)} datasets to {export_request.output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise ExportException(f"CSV export failed") from e


class LocalFileSystemRepository(FileSystemRepository):
    """Local file system implementation"""
    
    def ensure_directory_exists(self, path: Path) -> None:
        """Ensure directory exists"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {path}")
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            raise ExportException(f"Failed to create directory: {path}") from e
    
    def verify_file_created(self, path: Path) -> bool:
        """Verify file was created and has content"""
        try:
            if not path.exists():
                logger.error(f"File does not exist: {path}")
                return False
            
            if path.stat().st_size == 0:
                logger.error(f"File is empty: {path}")
                return False
            
            logger.debug(f"File verification passed: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify file {path}: {e}")
            return False