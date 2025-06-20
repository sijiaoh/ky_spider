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

# 运行爬虫（单个URL）
python main.py --url "https://example.com/path"

# 运行爬虫（多个URL）
python main.py --urls "https://url1.com" "https://url2.com"
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
- 避免可有可无的代码
- 避免没有必要的空值检查
- 避免大幅度的改写,要循序渐进,需要意识到更改的代码会由人检查

### 文件结构模式

- `src/` - 源代码模块
- `build/` - 输出文件目录
- 配置类在 `src/config.py`
- 主要逻辑在 `src/scraper.py`
- 数据处理在 `src/processor.py`
- 数据容器在 `src/table.py`

### 调试参数

- `--log-level DEBUG` 查看详细日志
- `--headless false` 显示浏览器操作
- `--log-file debug.log` 输出日志到文件

### 外部库

- 需要时用`uv add`加载.不要直接编辑project.toml
- 避免使用GitHub Star少的库

### Git 提交规范

- **严格禁止**：git commit 命令中的 commit message 禁止使用双引号，只能使用单引号
- **严格禁止**：git commit 命令中禁止使用 $() 语法
- 使用 HEREDOC 格式确保正确处理多行提交信息
- 示例正确格式：`git commit -m 'commit message'`
- 示例错误格式：`git commit -m "commit message"` ❌ 禁止使用
- 示例错误格式：`git commit -m '$(cat <<EOF...)'` ❌ 禁止使用

### 自我改进

- 意识到指令中包含今后也需要注意的事情时,记录到自我学习区里自我改进

## 智能提示

- 修改爬虫逻辑时重点关注 `src/scraper.py:FinancialDataScraper` 类
- 数据处理和合并逻辑在 `src/processor.py:FinancialDataProcessor` 类
- 添加新配置项在 `src/config.py:ScrapingConfig` 中定义
- 工具函数统一放在 `src/utils.py` 中

## 核心特性

### 数据完整性保障

- 严格异常退出：任何数据提取失败立即终止程序
- 文件完整性验证：检查输出文件存在性和内容
- SPA分页处理：正确处理单页应用的内容更新
- 表格加载等待：确保目标表格完全加载后再抓取
- 多数据源支持：支持多个URL或股票代码的数据合并，包含来源标识
- 日期对齐合并：不同数据源按日期列智能对齐，避免数据错位

### 技术架构

- Python 3.13+ 和 Playwright 异步爬虫
- 模块化设计：配置、爬虫、数据处理分离
- uv 包管理器提供快速依赖解析
- 支持直接URL输入和股票代码转换两种模式
- 面向对象数据结构：Table和FinancialTable类管理表格数据

## 自我学习区
<!-- Claude Code 在此记录新发现的项目模式和改进 -->

### 学到的规则
- Git commit 命令必须严格使用单引号，禁止双引号 - 违反此规则会被用户拒绝执行
- Git commit 命令禁止使用 $() 语法 - 违反此规则会被用户拒绝执行
- commit前必须运行git diff查看变更，以便生成准确的commit message

### 数据结构设计
- Table类：管理单个表格数据，包含名称、来源和DataFrame
- FinancialTable类：管理多个Table的集合，代表完整的金融数据
- 表格名称使用实际按钮文本而非索引，提高可读性
- 数据处理时保持层次结构：页面数据 → Table → FinancialTable → 最终输出
