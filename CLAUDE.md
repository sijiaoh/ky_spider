# Claude Code 项目配置

## 项目类型
Python 金融数据爬虫项目，使用 Playwright 和 pandas

## 快速命令

### 运行和测试
```bash
# 运行爬虫（单个股票代码）
python main.py --stock-code SH605136

# 运行爬虫（多个股票代码）
python main.py --stock-codes SH605136 SZ000001 SH000001
```

### 依赖管理
```bash
# 同步依赖
uv sync

# 安装浏览器
playwright install
```

## 项目约定

### 代码风格
- 函数和类使用类型注解
- 模块化设计，分离配置、爬虫逻辑和工具函数
- 严格的数据完整性检查，任何失败立即退出

### 文件结构模式
- `src/` - 源代码模块
- `build/` - 输出文件目录
- 配置类在 `src/config.py`
- 主要逻辑在 `src/scraper.py`

### 调试参数
- `--log-level DEBUG` 查看详细日志
- `--headless false` 显示浏览器操作
- `--log-file debug.log` 输出日志到文件

## 智能提示
- 修改爬虫逻辑时重点关注 `src/scraper.py:FinancialDataScraper` 类
- 添加新配置项在 `src/config.py:ScrapingConfig` 中定义
- 工具函数统一放在 `src/utils.py` 中

## 核心特性

### 数据完整性保障
- 严格异常退出：任何数据提取失败立即终止程序
- 文件完整性验证：检查输出文件存在性和内容
- SPA分页处理：正确处理单页应用的内容更新
- 表格加载等待：确保目标表格完全加载后再抓取
- 多股票代码支持：支持多个股票代码的数据纵向合并，包含来源标识

### 技术架构
- Python 3.13+ 和 Playwright 异步爬虫
- 模块化设计：配置、爬虫、工具分离
- uv 包管理器提供快速依赖解析

## 自我学习区
<!-- Claude Code 在此记录新发现的项目模式和改进 -->