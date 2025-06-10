from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScrapingConfig:
    """Configuration for the web scraping process"""
    base_url: str = "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html"
    stock_code: str = "SH605136"
    output_dir: Path = Path("build")
    output_filename: str = "zyzb_table.xlsx"
    headless: bool = True
    timeout: int = 10000
    
    @property
    def full_url(self) -> str:
        """Generate the full URL with stock code"""
        return f"{self.base_url}?type=web&code={self.stock_code}&color=b#/cwfx"
    
    @property
    def output_path(self) -> Path:
        """Generate the full output path"""
        return self.output_dir / self.output_filename