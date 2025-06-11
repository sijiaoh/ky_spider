from typing import List
from pathlib import Path

from ..domain.entities import StockCode, ScrapingTarget


class ScrapingTargetFactory:
    """Factory for creating scraping targets"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def create_target(self, stock_code: str) -> ScrapingTarget:
        """Create a single scraping target"""
        stock_code_obj = StockCode(stock_code)
        url = f"{self.base_url}?type=web&code={stock_code}&color=b#/cwfx"
        
        return ScrapingTarget(stock_code=stock_code_obj, url=url)
    
    def create_targets(self, stock_codes: List[str]) -> List[ScrapingTarget]:
        """Create multiple scraping targets"""
        return [self.create_target(code) for code in stock_codes]


class ConfigurationService:
    """Service for managing application configuration"""
    
    def __init__(
        self,
        base_url: str = "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html",
        default_output_dir: Path = Path("build"),
        default_output_filename: str = "zyzb_table.xlsx",
        default_headless: bool = True,
        default_timeout: int = 10000
    ):
        self.base_url = base_url
        self.default_output_dir = default_output_dir
        self.default_output_filename = default_output_filename
        self.default_headless = default_headless
        self.default_timeout = default_timeout
    
    def get_output_path(self, output_dir: Path = None, filename: str = None) -> Path:
        """Get full output path"""
        dir_path = output_dir or self.default_output_dir
        file_name = filename or self.default_output_filename
        return dir_path / file_name
    
    def create_target_factory(self) -> ScrapingTargetFactory:
        """Create a scraping target factory with configured base URL"""
        return ScrapingTargetFactory(self.base_url)