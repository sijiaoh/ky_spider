# Web版数据爬虫

简洁的Web界面，支持多URL数据爬取和下载。

## 启动

```bash
# 安装依赖
uv sync
playwright install

# 启动Web服务
python web_app.py
```

访问：http://localhost:8080

## 使用

1. 在文本框中输入URL（每行一个）
2. 点击"开始爬取"
3. 等待处理完成
4. 点击下载链接获取Excel文件

