# 金融数据爬虫工具

## 快速开始

### 安装依赖

```bash
# 使用uv包管理器（推荐）
uv sync

# 安装浏览器
playwright install
```

### 基本使用

```bash
# 使用股票代码
python main.py --stock-code SH605136

# 使用直接URL
python main.py --url "https://example.com/financial-data"

# 批量处理多个股票
python main.py --stock-codes SH605136 SZ000001 SH000001

# 批量处理多个URL
python main.py --urls "https://url1.com" "https://url2.com"
```

## 命令行参数

### 数据源参数（按优先级排序）

| 参数 | 描述 | 示例 |
|------|------|------|
| `--urls` | 多个URL（最高优先级） | `--urls "url1" "url2"` |
| `--url` | 单个URL | `--url "https://example.com"` |
| `--stock-codes` | 多个股票代码 | `--stock-codes SH605136 SZ000001` |
| `--stock-code` | 单个股票代码（默认） | `--stock-code SH605136` |

### 输出控制

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--output-dir` | `build` | 输出目录 |
| `--output-file` | `zyzb_table.xlsx` | 输出文件名 |

### 调试参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| `--log-level` | `INFO` | 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `--log-file` | - | 日志输出文件（可选） |
| `--headless` | `True` | 无头模式运行 |
| `--timeout` | `10000` | 页面超时时间（毫秒） |

## 项目结构

```
ky_spider/
├── src/
│   ├── config.py          # 配置管理
│   ├── scraper.py         # 网页爬取核心
│   ├── processor.py       # 数据处理和合并
│   └── utils.py          # 工具函数
├── build/                # 输出目录
├── main.py              # 程序入口
└── README.md           # 项目文档
```

## 调试技巧

```bash
# 查看详细执行过程
python main.py --log-level DEBUG --stock-code SH605136

# 显示浏览器操作（非无头模式）
python main.py --headless false --stock-code SH605136

# 输出日志到文件
python main.py --log-file debug.log --stock-code SH605136
```

## 技术栈

- **Python 3.13+** - 现代Python特性支持
- **Playwright** - 高性能浏览器自动化
- **pandas** - 数据处理和分析
- **BeautifulSoup** - HTML解析
- **cn2an** - 中文数字转换
- **uv** - 快速包管理

