from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class TableConfig:
    """Configuration for a single table extraction"""
    button_selector: Optional[str] = None
    table_selector: str = ".zyzb_table .report_table .table1"
    pagination_selector: str = ".zyzb_table .next"
    table_container_selector: str = ".zyzb_table"
    split_row_selector: Optional[str] = ".title"


@dataclass
class ScrapingConfig:
    """Configuration for the web scraping process"""
    base_url: str = "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html"
    stock_code: str = "SH605136"
    output_dir: Path = Path("build")
    output_filename: str = "zyzb_table.xlsx"
    headless: bool = True
    timeout: int = 10000
    tables: List[TableConfig] = None
    
    def __post_init__(self):
        if self.tables is None:
            self.tables = [
                TableConfig(
                    button_selector=".zyzb .title",
                    table_selector=".zyzb_table .report_table .table1",
                    pagination_selector=".zyzb_table .next",
                    table_container_selector=".zyzb_table",
                    split_row_selector=".zyzb_table .report_table .table1 .title td:nth-child(1)",
                ),
                TableConfig(
                    button_selector=".cwbbTab ul li:nth-child(1)",
                    table_selector="#report_zcfzb",
                    pagination_selector=".zcfzb_table .next",
                    table_container_selector=".zcfzb_table",
                    split_row_selector="#report_zcfzb .tips-fieldname-Left .font-bold",
                ),
                TableConfig(
                    button_selector=".cwbbTab ul li:nth-child(2)",
                    table_selector="#report_lrb",
                    pagination_selector=".lrb_table .next",
                    table_container_selector=".lrb_table",
                    split_row_selector="#report_lrb .tips-fieldname-Left .font-bold",
                ),
                TableConfig(
                    button_selector=".cwbbTab ul li:nth-child(3)",
                    table_selector="#report_xjllb",
                    pagination_selector=".xjllb_table .next",
                    table_container_selector=".xjllb_table",
                    split_row_selector="#report_xjllb .tips-fieldname-Left .font-bold",
                ),
            ]
    
    @property
    def full_url(self) -> str:
        """Generate the full URL with stock code"""
        return f"{self.base_url}?type=web&code={self.stock_code}&color=b#/cwfx"
    
    @property
    def output_path(self) -> Path:
        """Generate the full output path"""
        return self.output_dir / self.output_filename
