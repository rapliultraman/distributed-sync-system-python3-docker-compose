#!/usr/bin/env bash

# Test Runner Guide - Distributed Sync System
# Copy paste command yang mau dijalankan





  pip install pytest pytest-asyncio pytest-cov pytest-html pytest-xdist
  mkdir -p test_reports coverage



TEST 1: Unit Test - Lock Manager
  Testing lock manager component

  pytest tests/test_lock_manager.py \
      --html=test_reports/unit_lock_manager.html \
      --self-contained-html \
      --cov=src/nodes/lock_manager \
      --cov-report=html:coverage/lock_manager \
      --cov-report=term \
      -v

----------------------------------------

TEST 2: Unit Test - Queue System
  Testing queue node component

  pytest tests/test_queue.py \
      --html=test_reports/unit_queue.html \
      --self-contained-html \
      --cov=src/nodes/queue_node \
      --cov-report=html:coverage/queue_node \
      --cov-report=term \
      -v

----------------------------------------

TEST 3: Comprehensive Tests
  Running full test suite

  pytest tests/test_comprehensive.py \
      --html=test_reports/comprehensive_tests.html \
      --self-contained-html \
      --cov=src \
      --cov-report=html:coverage/comprehensive \
      --cov-report=term \
      --cov-report=xml:test_reports/coverage.xml \
      -v

----------------------------------------

TEST 4: API Endpoint Tests
  Testing API endpoints (perlu server running)

  Step 1 - Start test server:
  python -m src.nodes.base_node &
  
  Step 2 - Wait 5 seconds, then run test:
  pytest tests/test_api_endpoints.py \
      --html=test_reports/api_tests.html \
      --self-contained-html \
      --cov=src/api \
      --cov-report=html:coverage/api \
      --cov-report=term \
      -v
  
  Step 3 - Stop server:
  pkill -f "python -m src.nodes.base_node"

----------------------------------------

TEST 5: Integration Tests
  Testing dengan Docker cluster

  Step 1 - Start cluster:
  bash scripts/run_cluster.sh
  
  Step 2 - Wait 10 seconds, then run test:
  pytest tests/test_integration.py \
      --html=test_reports/integration_tests.html \
      --self-contained-html \
      -v
  
  Step 3 - Stop cluster:
  docker compose -f docker/docker-compose.yml down

----------------------------------------

TEST 6: Performance Tests
  Testing performance benchmarks

  Step 1 - Start cluster:
  bash scripts/run_cluster.sh
  
  Step 2 - Wait 10 seconds, then run test:
  pytest tests/test_performance.py \
      --html=test_reports/performance_tests.html \
      --self-contained-html \
      --benchmark-only \
      -v
  
  Step 3 - Stop cluster:
  docker compose -f docker/docker-compose.yml down

----------------------------------------

TEST 7: Parallel Tests
  Running tests in parallel untuk speed

  pytest tests/ \
      --html=test_reports/parallel_tests.html \
      --self-contained-html \
      --cov=src \
      --cov-report=html:coverage/parallel \
      --cov-report=term \
      -n auto \
      -v

----------------------------------------

TEST 8: Component-Specific Tests

  8a. Raft Consensus Tests:
  pytest tests/test_comprehensive.py::TestRaftRedis \
      --html=test_reports/raft_tests.html \
      --self-contained-html \
      -v

  8b. Lock Manager Tests:
  pytest tests/test_comprehensive.py::TestLockManager \
      --html=test_reports/lock_tests.html \
      --self-contained-html \
      -v

  8c. Cache Coherence Tests:
  pytest tests/test_comprehensive.py::TestCacheNode \
      --html=test_reports/cache_tests.html \
      --self-contained-html \
      -v

  8d. Queue System Tests:
  pytest tests/test_comprehensive.py::TestDistributedQueue \
      --html=test_reports/queue_tests.html \
      --self-contained-html \
      -v

  8e. Metrics Tests:
  pytest tests/test_comprehensive.py::TestMetricsCollector \
      --html=test_reports/metrics_tests.html \
      --self-contained-html \
      -v

========================================

QUICK TESTS (untuk demo):

  # Test specific function
  pytest tests/test_comprehensive.py::TestLockManager::test_basic_lock -v

  # Test with verbose output
  pytest tests/test_lock_manager.py -v -s

  # Test with coverage only
  pytest tests/test_queue.py --cov=src/nodes/queue_node --cov-report=term

  # Run single test file
  pytest tests/test_comprehensive.py -v

========================================

VIEW RESULTS:

  # HTML reports
  open test_reports/comprehensive_tests.html
  
  # Coverage reports
  open coverage/comprehensive/index.html
  
  # Check summary
  cat test_reports/test_summary.md

========================================

MONITORING:

  # Monitor Docker stats (jika pakai cluster)
  docker stats

  # Monitor logs
  docker compose -f docker/docker-compose.yml logs -f

  # Check node health
  curl http://localhost:8001/health
  curl http://localhost:8002/health
  curl http://localhost:8003/health

========================================

CLEANUP:

  # Remove cache files
  find . -name "__pycache__" -type d -exec rm -rf {} +
  find . -name "*.pyc" -delete
  find . -name ".pytest_cache" -type d -exec rm -rf {} +

  # Remove test reports (optional)
  rm -rf test_reports/* coverage/*

========================================
