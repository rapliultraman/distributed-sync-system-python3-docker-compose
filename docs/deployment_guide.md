# Distributed Sync System - Deployment Guide

## Overview

Distributed Sync System adalah implementasi sistem sinkronisasi terdistribusi yang mengimplementasikan:
- **Distributed Lock Manager** dengan Raft Consensus
- **Distributed Queue System** dengan Redis
- **Cache Coherence** dengan MESI Protocol
- **Performance Monitoring** dan Metrics

## Prerequisites

### System Requirements
- Docker dan Docker Compose
- Python 3.8+ (untuk development)
- Redis 7.0+
- Minimum 4GB RAM
- Minimum 2 CPU cores

### Software Dependencies
- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.8+ dengan pip
- Git

## Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd distributed-sync-system-2
```

### 2. Setup Environment
```bash
# Copy environment template
cp env.example .env

# Edit configuration jika diperlukan
nano .env
```

### 3. Start Cluster
```bash
# Build dan start semua services
bash scripts/run_cluster.sh
```

### 4. Verify Deployment
```bash
# Check health semua nodes
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Check leader election
curl http://localhost:8001/raft/leader
```

## Detailed Deployment

### Environment Configuration

File `.env` berisi konfigurasi berikut:

```bash
# Node Configuration
NODE_ID=node1
PEERS=node1,node2,node3
HTTP_PORT=8000

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Docker Environment Flag
DOCKER_ENV=1

# Cache Configuration
CACHE_CAPACITY=100

# Performance Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Heartbeat Configuration
HEARTBEAT_INTERVAL=1.0
HEARTBEAT_TIMEOUT=3.0

# Deadlock Detection
DEADLOCK_CHECK_INTERVAL=5.0

# Queue Configuration
QUEUE_PERSISTENCE=true
QUEUE_BACKUP_INTERVAL=60
```

### Docker Compose Services

Sistem terdiri dari 4 services:

1. **node1** (Port 8001)
2. **node2** (Port 8002) 
3. **node3** (Port 8003)
4. **redis** (Port 6379)

### Manual Deployment Steps

#### 1. Build Docker Images
```bash
docker compose -f docker/docker-compose.yml build
```

#### 2. Start Services
```bash
# Start semua services
docker compose -f docker/docker-compose.yml up -d

# Atau start individual service
docker compose -f docker/docker-compose.yml up -d redis
docker compose -f docker/docker-compose.yml up -d node1
docker compose -f docker/docker-compose.yml up -d node2
docker compose -f docker/docker-compose.yml up -d node3
```

#### 3. Scale Nodes (Optional)
```bash
# Scale ke 5 nodes
docker compose -f docker/docker-compose.yml up -d --scale node1=2 --scale node2=2 --scale node3=1
```

## Production Deployment

### 1. Production Environment Setup

```bash
# Create production environment file
cp env.example .env.production

# Update production settings
cat > .env.production << EOF
NODE_ID=prod-node1
PEERS=prod-node1,prod-node2,prod-node3
HTTP_PORT=8000
REDIS_URL=redis://redis-prod:6379/0
DOCKER_ENV=1
CACHE_CAPACITY=1000
ENABLE_METRICS=true
LOG_LEVEL=WARNING
HEARTBEAT_INTERVAL=0.5
HEARTBEAT_TIMEOUT=2.0
DEADLOCK_CHECK_INTERVAL=3.0
QUEUE_PERSISTENCE=true
EOF
```

### 2. Production Docker Compose

```yaml
version: "3.8"
services:
  redis-prod:
    image: redis:7
    ports:
      - "6379:6379"
    command: ["redis-server", "--save", "60", "1", "--maxmemory", "2gb"]
    volumes:
      - redis_data:/data
    restart: unless-stopped

  prod-node1:
    build:
      context: ..
      dockerfile: docker/Dockerfile.node
    env_file:
      - ../.env.production
    environment:
      NODE_ID: prod-node1
      PEERS: prod-node2,prod-node3
    ports:
      - "8001:8000"
    depends_on:
      - redis-prod
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

volumes:
  redis_data:
```

### 3. Load Balancer Configuration (Nginx)

```nginx
upstream distributed_sync {
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}

server {
    listen 80;
    server_name distributed-sync.local;

    location / {
        proxy_pass http://distributed_sync;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Monitoring dan Observability

### 1. Metrics Endpoint

Setiap node menyediakan metrics endpoint:

```bash
# JSON format
curl http://localhost:8001/metrics

# Prometheus format
curl http://localhost:8001/metrics?format=prometheus
```

### 2. Health Checks

```bash
# Basic health check
curl http://localhost:8001/health

# Detailed system status
curl http://localhost:8001/cache/state
curl http://localhost:8001/raft/log
```

### 3. Log Monitoring

```bash
# View logs
docker compose -f docker/docker-compose.yml logs -f node1

# View specific log files
tail -f logs/node1.log
tail -f logs/node1_structured.log
```

## Performance Testing

### 1. Load Testing dengan Locust

```bash
# Install Locust
pip install locust

# Run load tests
bash scripts/run_load_tests.sh

# Manual load test
locust -f benchmarks/load_test_scenarios.py --host=http://localhost:8001 --users=50 --spawn-rate=5 --run-time=5m --headless
```

### 2. Stress Testing

```bash
# Lock stress test
locust -f benchmarks/load_test_scenarios.py:LockStressTestUser --host=http://localhost:8001 --users=20 --spawn-rate=10 --run-time=2m --headless

# Cache coherence test
locust -f benchmarks/load_test_scenarios.py:CacheCoherenceTestUser --host=http://localhost:8001 --users=30 --spawn-rate=5 --run-time=3m --headless
```

## Troubleshooting

### Common Issues

#### 1. Redis Connection Failed
**Symptoms:**
- Nodes tidak bisa connect ke Redis
- Error: "Redis connection failed"

**Solutions:**
```bash
# Check Redis status
docker compose -f docker/docker-compose.yml ps redis

# Restart Redis
docker compose -f docker/docker-compose.yml restart redis

# Check Redis logs
docker compose -f docker/docker-compose.yml logs redis

# Test Redis connection
docker exec -it distributed-sync-system-2-redis-1 redis-cli ping
```

#### 2. Leader Election Issues
**Symptoms:**
- Tidak ada leader yang terpilih
- Multiple leaders
- Frequent leader changes

**Solutions:**
```bash
# Check leader status semua nodes
curl http://localhost:8001/raft/leader
curl http://localhost:8002/raft/leader
curl http://localhost:8003/raft/leader

# Check Raft log
curl http://localhost:8001/raft/log

# Restart problematic node
docker compose -f docker/docker-compose.yml restart node1
```

#### 3. Lock Deadlocks
**Symptoms:**
- Lock tidak bisa di-acquire
- System hang
- Deadlock detection alerts

**Solutions:**
```bash
# Check wait-for graph
curl http://localhost:8001/locks/wait_for

# Force release locks (emergency)
curl -X POST http://localhost:8001/locks/release -H "Content-Type: application/json" -d '{"resource":"problematic_resource","owner":"any_owner"}'

# Check deadlock detection logs
grep "Deadlock detected" logs/node1.log
```

#### 4. Cache Inconsistency
**Symptoms:**
- Cache values tidak konsisten antar nodes
- Cache misses tinggi
- Invalid cache states

**Solutions:**
```bash
# Check cache state
curl http://localhost:8001/cache/state
curl http://localhost:8002/cache/state
curl http://localhost:8003/cache/state

# Clear cache (emergency)
curl -X POST http://localhost:8001/cache/invalidate -H "Content-Type: application/json" -d '{"key":"problematic_key"}'

# Check cache metrics
curl http://localhost:8001/metrics | grep cache
```

#### 5. Queue Message Loss
**Symptoms:**
- Messages hilang dari queue
- Consumer tidak mendapat messages
- Queue empty padahal ada producer

**Solutions:**
```bash
# Check Redis queue data
docker exec -it distributed-sync-system-2-redis-1 redis-cli
> KEYS queue:*
> LLEN queue:topic_name

# Check queue persistence
docker compose -f docker/docker-compose.yml logs redis | grep "save"

# Restart Redis dengan persistence
docker compose -f docker/docker-compose.yml restart redis
```

### Performance Issues

#### 1. High Latency
**Symptoms:**
- Response time tinggi
- Slow lock acquisition
- Delayed message processing

**Solutions:**
```bash
# Check system metrics
curl http://localhost:8001/metrics

# Monitor resource usage
docker stats

# Check network latency
ping redis
ping node1
ping node2
ping node3

# Optimize configuration
# Reduce HEARTBEAT_INTERVAL
# Increase CACHE_CAPACITY
# Adjust DEADLOCK_CHECK_INTERVAL
```

#### 2. Memory Issues
**Symptoms:**
- High memory usage
- Out of memory errors
- Slow performance

**Solutions:**
```bash
# Check memory usage
docker stats

# Monitor Redis memory
docker exec -it distributed-sync-system-2-redis-1 redis-cli info memory

# Clear cache jika perlu
curl -X POST http://localhost:8001/cache/invalidate -H "Content-Type: application/json" -d '{"key":"*"}'

# Restart services
docker compose -f docker/docker-compose.yml restart
```

### Network Issues

#### 1. Inter-node Communication Failed
**Symptoms:**
- Nodes tidak bisa komunikasi
- Heartbeat failures
- Network partition

**Solutions:**
```bash
# Check network connectivity
docker network ls
docker network inspect distributed-sync-system-2_default

# Test inter-node communication
docker exec -it distributed-sync-system-2-node1-1 curl http://node2:8000/health
docker exec -it distributed-sync-system-2-node1-1 curl http://node3:8000/health

# Restart network
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d
```

## Maintenance

### 1. Regular Maintenance Tasks

#### Daily
- Check health semua nodes
- Monitor error logs
- Check Redis persistence

#### Weekly
- Review performance metrics
- Check disk space
- Update dependencies

#### Monthly
- Full system backup
- Performance analysis
- Security updates

### 2. Backup Procedures

```bash
# Backup Redis data
docker exec distributed-sync-system-2-redis-1 redis-cli BGSAVE
docker cp distributed-sync-system-2-redis-1:/data/dump.rdb ./backup/

# Backup logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/

# Backup configuration
cp .env ./backup/env_backup_$(date +%Y%m%d)
```

### 3. Update Procedures

```bash
# Update system
git pull origin main

# Rebuild images
docker compose -f docker/docker-compose.yml build

# Rolling update
docker compose -f docker/docker-compose.yml up -d --no-deps node1
sleep 30
docker compose -f docker/docker-compose.yml up -d --no-deps node2
sleep 30
docker compose -f docker/docker-compose.yml up -d --no-deps node3

# Verify update
bash scripts/run_cluster.sh
```

## Security Considerations

### 1. Network Security
- Gunakan firewall untuk membatasi akses
- Enkripsi komunikasi antar nodes
- Isolasi network dengan Docker networks

### 2. Data Security
- Enkripsi Redis data
- Secure backup procedures
- Access control untuk API endpoints

### 3. Monitoring Security
- Monitor failed login attempts
- Log semua security events
- Regular security audits

## Support dan Kontak

Untuk bantuan lebih lanjut:
- Dokumentasi API: `docs/api_spec.yaml`
- Log files: `logs/`
- Performance reports: `benchmark_results/`

## Appendix

### A. Port Configuration
- Node1: 8001
- Node2: 8002  
- Node3: 8003
- Redis: 6379
- Metrics: 9090 (optional)

### B. Environment Variables Reference
Lihat file `env.example` untuk daftar lengkap environment variables.

### C. API Endpoints Reference
Lihat file `docs/api_spec.yaml` untuk dokumentasi lengkap API endpoints.
