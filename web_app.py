#!/usr/bin/env python3
"""
金融数据爬虫Web应用
"""

import uuid
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file, render_template

from src.config import ScrapingConfig
from src.scraper import FinancialDataScraper
from src.processor import FinancialDataProcessor

app = Flask(__name__)

# 创建输出目录
OUTPUT_DIR = Path('downloads')
OUTPUT_DIR.mkdir(exist_ok=True)

# 任务状态存储（线程安全）
tasks = {}
tasks_lock = threading.Lock()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    urls = request.json.get('urls', [])
    if not urls or len(urls) > 20:
        return jsonify({'error': 'Invalid URLs'}), 400
    
    task_id = str(uuid.uuid4())[:8]
    with tasks_lock:
        tasks[task_id] = {'status': 'processing'}
    
    # 后台处理
    threading.Thread(target=process_urls, args=(urls, task_id), daemon=True).start()
    
    return jsonify({'task_id': task_id})

def process_urls(urls, task_id):
    try:
        # 创建输出文件名
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = OUTPUT_DIR / filename
        
        # 配置爬虫
        config = ScrapingConfig(
            stock_code="WEB",
            output_dir=OUTPUT_DIR,
            output_filename=filename,
            headless=True,
            timeout=15000
        )
        
        # 执行爬取和处理
        scraper = FinancialDataScraper(config)
        processor = FinancialDataProcessor(config)
        
        scraped_data = scraper.run(urls)
        processor.process_and_save_data(scraped_data)
        
        with tasks_lock:
            tasks[task_id] = {'status': 'completed', 'file': str(output_path)}
        
    except Exception as e:
        with tasks_lock:
            tasks[task_id] = {'status': 'error', 'error': str(e)}

@app.route('/status/<task_id>')
def status(task_id):
    with tasks_lock:
        return jsonify(tasks.get(task_id, {'status': 'not_found'}))

@app.route('/download/<task_id>')
def download(task_id):
    with tasks_lock:
        task = tasks.get(task_id)
        if not task or task.get('status') != 'completed':
            return 'File not ready', 404
        file_path = task['file']
    
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    print("启动服务: http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080)
