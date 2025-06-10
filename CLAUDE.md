# Claude Code 项目配置

## 项目类型
Python 金融数据爬虫项目，使用 Playwright 和 pandas

## 快速命令

### 运行和测试
```bash
# 运行爬虫
python main.py

# 运行并检查代码质量
python main.py && ruff check . && ruff format .
```

### 代码质量检查
```bash
# 格式化和检查
ruff format . && ruff check .
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
- 使用 ruff 进行代码格式化和检查
- 函数和类使用类型注解
- 模块化设计，分离配置、爬虫逻辑和工具函数

### 文件结构模式
- `src/` - 源代码模块
- `build/` - 输出文件目录
- 配置类在 `src/config.py`
- 主要逻辑在 `src/scraper.py`

### 常用调试
- 使用 `--log-level DEBUG` 查看详细日志
- 使用 `--headless false` 查看浏览器操作
- 日志文件输出到指定路径进行分析

## 智能提示
- 修改爬虫逻辑时重点关注 `src/scraper.py:FinancialDataScraper` 类
- 添加新配置项在 `src/config.py:ScrapingConfig` 中定义
- 工具函数统一放在 `src/utils.py` 中

## 自我完善记录
<!-- Claude Code 会在这里自动记录项目改进和学习内容 -->

### 项目发现和改进建议
- 项目使用 Python 3.13+ 和现代异步爬虫技术
- 已建立模块化架构，便于维护和扩展
- 使用 uv 作为包管理器，性能优于传统 pip

### 数据完整性保障机制
- ✅ 2025-01-06: 实施严格的异常退出机制
  - 任何数据提取失败立即抛出 RuntimeError
  - 空表格、空数据框或文件创建失败都会终止程序
  - 所有异常都会正确传播到主程序并退出
  - 输出文件完整性验证（文件存在性和非空检查）

### 待补充内容
<!-- 在后续对话中根据需要添加新的发现和改进 -->