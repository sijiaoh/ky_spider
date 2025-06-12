# Docker部署指南

使用Docker容器化部署金融数据爬虫Web应用。

## 快速部署

### 使用Docker Compose（推荐）

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 使用Docker命令

```bash
# 构建镜像
docker build -t ky-spider .

# 运行容器
docker run -d \
  --name ky-spider \
  -p 8080:8080 \
  -v $(pwd)/downloads:/app/downloads \
  ky-spider
```

## 访问应用

部署成功后访问：http://localhost:8080

## 生产环境配置

### 反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 环境变量

```bash
# docker-compose.yml中添加
environment:
  - FLASK_ENV=production
  - FLASK_DEBUG=false
```

## 维护

```bash
# 查看容器状态
docker-compose ps

# 重启服务
docker-compose restart

# 更新应用
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```