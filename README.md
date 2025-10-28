# Distributed Sync System

Sistem sinkronisasi terdistribusi yang mengimplementasikan algoritma consensus, distributed locking, queue management, dan cache coherence untuk skenario real-world distributed systems.

## 🚀 Features

### Core Components

- **🔒 Distributed Lock Manager** - Implementasi distributed lock menggunakan Raft Consensus Algorithm
- **📬 Distributed Queue System** - Sistem queue terdistribusi dengan Redis dan consistent hashing
- **💾 Cache Coherence** - Implementasi MESI protocol untuk cache coherence
- **📊 Performance Monitoring** - Metrics collection dan monitoring dengan Prometheus format
- **🐳 Containerization** - Docker containerization dengan orchestration support

### Advanced Features

- **🔄 Raft Consensus** - Leader election dan log replication
- **🚫 Deadlock Detection** - Automatic deadlock detection dan resolution
- **📈 Load Testing** - Comprehensive load testing dengan Locust
- **📚 API Documentation** - Complete OpenAPI/Swagger specification
- **🧪 Test Suite** - Comprehensive test coverage dengan unit, integration, dan performance tests

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Node 1      │    │     Node 2      │    │     Node 3      │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Raft        │ │◄──►│ │ Raft        │ │◄──►│ │ Raft        │ │
│ │ Consensus   │ │    │ │ Consensus   │ │    │ │ Consensus   │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Lock        │ │◄──►│ │ Lock        │ │◄──►│ │ Lock        │ │
│ │ Manager     │ │    │ │ Manager     │ │    │ │ Manager     │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Cache       │ │◄──►│ │ Cache       │ │◄──►│ │ Cache       │ │
│ │ (MESI)      │ │    │ │ (MESI)      │ │    │ │ (MESI)      │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Queue       │ │    │ │ Queue       │ │    │ │ Queue       │ │
│ │ System      │ │    │ │ System      │ │    │ │ System      │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │      Redis       │
                    │   (Shared Log)   │
                    └─────────────────┘
```

## 🛠️ Technology Stack

- **Python 3.8+** dengan asyncio untuk asynchronous programming
- **Redis 7.0+** untuk distributed state management
- **Docker & Docker Compose** untuk containerization
- **aiohttp** untuk HTTP API server
- **Locust** untuk load testing
- **pytest** untuk testing framework
- **Prometheus** format untuk metrics

## 📦 Installation & Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.8+ (untuk development)
- Git

### Quick Start

```bash
# Clone repository
git clone <repository-url>
cd distributed-sync-system-2

# Setup environment
cp env.example .env

# Start cluster
bash scripts/run_cluster.sh

# Verify deployment
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
bash scripts/run_tests.sh

# Run load tests
bash scripts/run_load_tests.sh
```

## 🔧 Configuration

### Environment Variables

```bash
# Node Configuration
NODE_ID=node1
PEERS=node1,node2,node3
HTTP_PORT=8000

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Cache Configuration
CACHE_CAPACITY=100

# Performance Monitoring
ENABLE_METRICS=true
LOG_LEVEL=INFO

# Heartbeat Configuration
HEARTBEAT_INTERVAL=1.0
HEARTBEAT_TIMEOUT=3.0
```

## 📡 API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /raft/leader` - Current leader information
- `GET /metrics` - System metrics (JSON/Prometheus format)

### Raft Consensus
- `POST /raft/heartbeat` - Send heartbeat
- `POST /raft/append` - Append command to log
- `GET /raft/log` - Get log entries

### Distributed Locks
- `POST /locks/acquire` - Acquire lock
- `POST /locks/release` - Release lock
- `GET /locks/wait_for` - Get wait-for graph

### Queue System
- `POST /queue/produce` - Produce message
- `POST /queue/consume` - Consume message

### Cache Coherence
- `GET /cache/get` - Get cache value
- `POST /cache/put` - Put cache value
- `POST /cache/invalidate` - Invalidate cache
- `GET /cache/fetch` - Fetch from peer
- `GET /cache/state` - Cache state and metrics

## 🧪 Testing

### Test Suite

```bash
# Run all tests
bash scripts/run_tests.sh

# Run specific test categories
pytest tests/test_comprehensive.py
pytest tests/test_api_endpoints.py
pytest tests/test_lock_manager.py
pytest tests/test_queue.py
```

### Load Testing

```bash
# Run comprehensive load tests
bash scripts/run_load_tests.sh

# Manual load testing
locust -f benchmarks/load_test_scenarios.py --host=http://localhost:8001 --users=50 --spawn-rate=5 --run-time=5m --headless
```

### Test Coverage

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component testing
- **API Tests**: Endpoint testing
- **Performance Tests**: Load dan stress testing
- **Cache Coherence Tests**: MESI protocol testing

## 📊 Performance Monitoring

### Metrics Available

- **System Metrics**: CPU, Memory, Disk, Network
- **Raft Metrics**: Leader election, Log replication
- **Lock Metrics**: Acquire/release latency, Deadlock detection
- **Cache Metrics**: Hit/miss ratios, State transitions
- **Queue Metrics**: Produce/consume throughput

### Monitoring Endpoints

```bash
# JSON format metrics
curl http://localhost:8001/metrics

# Prometheus format metrics
curl http://localhost:8001/metrics?format=prometheus

# Cache state
curl http://localhost:8001/cache/state
```

## 🐳 Docker Deployment

### Production Deployment

```bash
# Production environment
cp env.example .env.production

# Start production cluster
docker compose -f docker/docker-compose.yml up -d

# Scale nodes
docker compose -f docker/docker-compose.yml up -d --scale node1=2 --scale node2=2 --scale node3=1
```

### Container Management

```bash
# View logs
docker compose -f docker/docker-compose.yml logs -f node1

# Restart services
docker compose -f docker/docker-compose.yml restart node1

# Scale services
docker compose -f docker/docker-compose.yml up -d --scale node1=3
```

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   docker compose -f docker/docker-compose.yml restart redis
   ```

2. **Leader Election Issues**
   ```bash
   curl http://localhost:8001/raft/leader
   curl http://localhost:8002/raft/leader
   curl http://localhost:8003/raft/leader
   ```

3. **Lock Deadlocks**
   ```bash
   curl http://localhost:8001/locks/wait_for
   ```

4. **Cache Inconsistency**
   ```bash
   curl http://localhost:8001/cache/state
   ```

### Log Analysis

```bash
# View application logs
tail -f logs/node1.log

# View structured logs
tail -f logs/node1_structured.log

# View Docker logs
docker compose -f docker/docker-compose.yml logs -f
```

## 📚 Documentation

- **[API Documentation](docs/api_spec.yaml)** - Complete OpenAPI/Swagger specification
- **[Deployment Guide](docs/deployment_guide.md)** - Detailed deployment dan troubleshooting guide
- **[Architecture Overview](docs/architecture.md)** - System architecture documentation

## 🎯 Use Cases

### Distributed Lock Manager
- Database transaction coordination
- Resource access control
- Critical section protection

### Distributed Queue System
- Message processing
- Task distribution
- Event streaming

### Cache Coherence
- Distributed caching
- Data consistency
- Performance optimization

## 🚀 Performance Characteristics

### Benchmarks
- **Lock Operations**: < 10ms latency
- **Queue Throughput**: > 1000 messages/second
- **Cache Hit Ratio**: > 90% dengan proper sizing
- **Leader Election**: < 1 second recovery time

### Scalability
- **Horizontal Scaling**: Support untuk multiple nodes
- **Load Distribution**: Automatic load balancing
- **Fault Tolerance**: Handle node failures gracefully

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Add tests untuk new features
4. Ensure all tests pass
5. Submit pull request

## 📄 License

MIT License - see LICENSE file untuk details.

## 🆘 Support

Untuk bantuan dan pertanyaan:
- Dokumentasi: `docs/`
- Issues: GitHub Issues
- Logs: `logs/` directory

## 🎓 Educational Value

Proyek ini mengimplementasikan konsep-konsep penting dalam distributed systems:

- **Consensus Algorithms** (Raft)
- **Distributed Locking**
- **Cache Coherence Protocols** (MESI)
- **Message Passing**
- **Fault Tolerance**
- **Performance Monitoring**

Sangat cocok untuk pembelajaran dan penelitian dalam bidang distributed systems.
