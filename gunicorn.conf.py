# Tuned for e2-micro (1 GB RAM): one process, threaded workers, shared app memory.
bind = "0.0.0.0:5000"
workers = 1
threads = 4
worker_class = "gthread"
timeout = 60
graceful_timeout = 30
keepalive = 5
preload_app = True
max_requests = 1000
max_requests_jitter = 100
