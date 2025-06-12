# Gunicorn configuration for small-scale production
bind = "0.0.0.0:8080"
workers = 1
worker_class = "sync"
worker_connections = 100
max_requests = 500
max_requests_jitter = 50
timeout = 120
keepalive = 2
preload_app = True