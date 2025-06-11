import argparse
import sys
from pathlib import Path
from typing import List

from ..application.use_cases import ScrapingWorkflow, ScrapeFinancialDataUseCase, ExportFinancialDataUseCase
from ..application.services import ConfigurationService
from ..infrastructure.web_scraping import PlaywrightWebScrapingRepository
from ..infrastructure.data_processing import BeautifulSoupDataProcessor
from ..infrastructure.chinese_converter import Cn2anChineseConverter
from ..infrastructure.validation import StrictDataValidator
from ..infrastructure.file_system import PandasDataExporter, LocalFileSystemRepository
from ..infrastructure.logging import setup_logging
from ..domain.exceptions import DomainException


class CLIInterface:
    """Command Line Interface for the financial data scraper"""
    
    def __init__(self):
        self.config_service = ConfigurationService()
    
    def parse_arguments(self) -> argparse.Namespace:
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="Scrape financial data from Eastmoney website"
        )
        parser.add_argument(
            "--stock-code",
            default="SH605136",
            help="Stock code to scrape (default: SH605136)"
        )
        parser.add_argument(
            "--stock-codes",
            nargs="+",
            help="Multiple stock codes to scrape (overrides stock-code if provided)"
        )
        parser.add_argument(
            "--output-dir",
            type=Path,
            default=self.config_service.default_output_dir,
            help="Output directory (default: build)"
        )
        parser.add_argument(
            "--output-file",
            default=self.config_service.default_output_filename,
            help="Output filename (default: zyzb_table.xlsx)"
        )
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Logging level (default: INFO)"
        )
        parser.add_argument(
            "--log-file",
            type=Path,
            help="Log file path (optional)"
        )
        parser.add_argument(
            "--headless",
            action="store_true",
            default=self.config_service.default_headless,
            help="Run browser in headless mode (default: True)"
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=self.config_service.default_timeout,
            help="Page timeout in milliseconds (default: 10000)"
        )
        
        return parser.parse_args()
    
    def _setup_dependencies(self, args: argparse.Namespace) -> ScrapingWorkflow:
        """Setup dependency injection"""
        # Infrastructure layer
        file_system = LocalFileSystemRepository()
        chinese_converter = Cn2anChineseConverter()
        validator = StrictDataValidator()
        data_processor = BeautifulSoupDataProcessor(chinese_converter, validator)
        data_exporter = PandasDataExporter(file_system)
        
        # Application layer
        scrape_use_case = ScrapeFinancialDataUseCase(None, data_processor)  # Web repo will be injected
        export_use_case = ExportFinancialDataUseCase(data_exporter)
        
        return ScrapingWorkflow(scrape_use_case, export_use_case)
    
    def _get_stock_codes(self, args: argparse.Namespace) -> List[str]:
        """Get stock codes from arguments"""
        if args.stock_codes:
            return args.stock_codes
        else:
            return [args.stock_code]
    
    def run(self) -> int:
        """Main entry point"""
        try:
            args = self.parse_arguments()
            
            # Setup logging
            setup_logging(args.log_level, args.log_file)
            
            # Setup dependencies
            workflow = self._setup_dependencies(args)
            
            # Get stock codes and create targets
            stock_codes = self._get_stock_codes(args)
            target_factory = self.config_service.create_target_factory()
            targets = target_factory.create_targets(stock_codes)
            
            # Get output path
            output_path = self.config_service.get_output_path(args.output_dir, args.output_file)
            
            # Setup web scraping repository with context manager
            with PlaywrightWebScrapingRepository(args.headless, args.timeout) as web_repo:
                # Inject web repository
                workflow.scrape_use_case.web_scraping_repo = web_repo
                
                # Execute workflow
                workflow.execute(targets, output_path)
            
            return 0
            
        except KeyboardInterrupt:
            print("\nProcess interrupted by user")
            return 1
        except DomainException as e:
            print(f"Error: {e}", file=sys.stderr)
            print("Process terminated due to data integrity failure", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Critical Error: {e}", file=sys.stderr)
            print("Process terminated due to unexpected error", file=sys.stderr)
            return 1


def cli_main() -> int:
    """CLI entry point"""
    cli = CLIInterface()
    return cli.run()