#!/usr/bin/env bash

# Load Testing Commands - Distributed Sync System
# Copy paste command yang mau dijalankan


DISTRIBUTED SYNC LOAD TESTING



TEST 1: General Load Test
  Testing semua endpoint dengan beban normal

  locust -f benchmarks/load_test_scenarios.py \
      --host=http://localhost:8001 \
      --users=50 \
      --spawn-rate=5 \
      --run-time=5m \
      --headless \
      --html=test_reports/general_test.html


TEST 2: Lock Stress Test
  Testing lock operations dengan beban tinggi

  locust -f benchmarks/load_test_scenarios.py \
      --host=http://localhost:8001 \
      --users=20 \
      --spawn-rate=10 \
      --run-time=2m \
      --headless \
      --html=test_reports/lock_test.html \
      LockStressTestUser


TEST 3: Cache Coherence Test
  Testing cache coherence multiple nodes

  locust -f benchmarks/load_test_scenarios.py CacheCoherenceTestUser \
      --host=http://localhost:8001 \
      --users=30 \
      --spawn-rate=5 \
      --run-time=3m \
      --headless \
      --html=test_reports/cache_test.html


TEST 4: Queue Throughput Test
  Testing queue throughput dengan beban tinggi

  locust -f benchmarks/load_test_scenarios.py QueueThroughputTestUser \
      --host=http://localhost:8001 \
      --users=100 \
      --spawn-rate=20 \
      --run-time=2m \
      --headless \
      --html=test_reports/queue_test.html


TEST 5: Multi-Node Test
  Testing distribusi beban ke 3 nodes

  Node 1:
  locust -f benchmarks/load_test_scenarios.py \
      --host=http://localhost:8001 \
      --users=25 --spawn-rate=5 --run-time=1m \
      --headless --html=test_reports/node1_test.html

  Node 2:
  locust -f benchmarks/load_test_scenarios.py \
      --host=http://localhost:8002 \
      --users=25 --spawn-rate=5 --run-time=1m \
      --headless --html=test_reports/node2_test.html

  Node 3:
  locust -f benchmarks/load_test_scenarios.py \
      --host=http://localhost:8003 \
      --users=25 --spawn-rate=5 --run-time=1m \
      --headless --html=test_reports/node3_test.html


Bersamaan dengan 3 terminal di jalankan 

    locust -f benchmarks/load_test_scenarios.py -H http://localhost:8001 -u 25 -r 5 -t 1m --headless --html=test_reports/node1.html
    locust -f benchmarks/load_test_scenarios.py -H http://localhost:8002 -u 25 -r 5 -t 1m --headless --html=test_reports/node2.html
    locust -f benchmarks/load_test_scenarios.py -H http://localhost:8003 -u 25 -r 5 -t 1m --headless --html=test_reports/node3.html

    curl http://localhost:8001/health
    curl http://localhost:8002/health
    curl http://localhost:8003/health



DEMO MODE (Quick 30s tests):

  locust -f benchmarks/load_test_scenarios.py \
      --host=http://localhost:8001 \
      --users=20 --spawn-rate=5 --run-time=30s \
      --headless --html=test_reports/demo.html

WEB UI MODE (Recommended):

  locust -f benchmarks/load_test_scenarios.py \
      --host=http://localhost:8001
  
  Buka: http://localhost:8089

