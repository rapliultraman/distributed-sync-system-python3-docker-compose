import random
import time
from locust import HttpUser, task, between
import json

class DistributedSystemUser(HttpUser):
    """Load testing untuk Distributed Sync System"""
    
    wait_time = between(0.1, 1.0)  # Random wait between requests
    
    def on_start(self):
        """Setup awal untuk setiap user"""
        self.node_id = f"client_{random.randint(1000, 9999)}"
        self.resources = [f"resource_{i}" for i in range(1, 11)]
        self.topics = [f"topic_{i}" for i in range(1, 6)]
        self.cache_keys = [f"key_{i}" for i in range(1, 21)]
        
    @task(3)
    def health_check(self):
        """Health check endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    response.success()
                else:
                    response.failure("Health check failed")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def get_leader(self):
        """Get current leader"""
        with self.client.get("/raft/leader", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if 'leader' in data and 'term' in data:
                    response.success()
                else:
                    response.failure("Invalid leader response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(5)
    def acquire_lock(self):
        """Acquire distributed lock"""
        resource = random.choice(self.resources)
        mode = random.choice(['shared', 'exclusive'])
        
        payload = {
            'resource': resource,
            'owner': self.node_id,
            'mode': mode
        }
        
        with self.client.post("/locks/acquire", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    response.success()
                    # Simulate work with lock
                    time.sleep(random.uniform(0.1, 0.5))
                    # Release lock
                    self.release_lock(resource)
                else:
                    response.failure("Lock acquisition failed")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def release_lock(self, resource):
        """Release distributed lock"""
        payload = {
            'resource': resource,
            'owner': self.node_id
        }
        
        with self.client.post("/locks/release", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    response.success()
                else:
                    response.failure("Lock release failed")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(4)
    def produce_message(self):
        """Produce message to queue"""
        topic = random.choice(self.topics)
        message = f"message_{self.node_id}_{int(time.time())}"
        
        payload = {
            'topic': topic,
            'message': message
        }
        
        with self.client.post("/queue/produce", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    response.success()
                else:
                    response.failure("Message production failed")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)
    def consume_message(self):
        """Consume message from queue"""
        topic = random.choice(self.topics)
        
        payload = {
            'topic': topic
        }
        
        with self.client.post("/queue/consume", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if 'message' in data:
                    response.success()
                else:
                    response.failure("Message consumption failed")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(6)
    def cache_operations(self):
        """Cache operations (get/put)"""
        key = random.choice(self.cache_keys)
        value = f"value_{self.node_id}_{int(time.time())}"
        
        # Put operation
        payload = {
            'key': key,
            'value': value
        }
        
        with self.client.post("/cache/put", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    response.success()
                else:
                    response.failure("Cache put failed")
            else:
                response.failure(f"HTTP {response.status_code}")
        
        # Get operation
        with self.client.get(f"/cache/get?key={key}", 
                            catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if 'value' in data:
                    response.success()
                else:
                    response.failure("Cache get failed")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_cache_state(self):
        """Get cache state for monitoring"""
        with self.client.get("/cache/state", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if 'cache_state' in data and 'metrics' in data:
                    response.success()
                else:
                    response.failure("Invalid cache state response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_metrics(self):
        """Get system metrics"""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if 'node_id' in data and 'uptime_seconds' in data:
                    response.success()
                else:
                    response.failure("Invalid metrics response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_raft_log(self):
        """Get Raft log"""
        with self.client.get("/raft/log", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if 'log' in data:
                    response.success()
                else:
                    response.failure("Invalid log response")
            else:
                response.failure(f"HTTP {response.status_code}")


class LockStressTestUser(HttpUser):
    """Stress test khusus untuk lock operations"""
    
    wait_time = between(0.01, 0.1)  # Very fast requests
    
    def on_start(self):
        self.node_id = f"stress_client_{random.randint(1000, 9999)}"
        self.resource = "stress_resource"
    
    @task(10)
    def rapid_lock_operations(self):
        """Rapid lock acquire/release operations"""
        # Acquire
        payload = {
            'resource': self.resource,
            'owner': self.node_id,
            'mode': 'exclusive'
        }
        
        with self.client.post("/locks/acquire", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    response.success()
                    # Immediate release
                    self.client.post("/locks/release", 
                                    json={'resource': self.resource, 'owner': self.node_id})
                else:
                    response.failure("Lock acquisition failed")
            else:
                response.failure(f"HTTP {response.status_code}")


class CacheCoherenceTestUser(HttpUser):
    """Test khusus untuk cache coherence"""
    
    wait_time = between(0.1, 0.3)
    
    def on_start(self):
        self.node_id = f"cache_client_{random.randint(1000, 9999)}"
        self.test_key = "coherence_test_key"
    
    @task(5)
    def cache_coherence_test(self):
        """Test cache coherence dengan multiple operations"""
        value = f"value_{self.node_id}_{int(time.time())}"
        
        # Put value
        payload = {
            'key': self.test_key,
            'value': value
        }
        
        with self.client.post("/cache/put", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Cache put failed: HTTP {response.status_code}")
        
        # Get value
        with self.client.get(f"/cache/get?key={self.test_key}", 
                            catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Cache get failed: HTTP {response.status_code}")
        
        # Invalidate
        payload = {'key': self.test_key}
        with self.client.post("/cache/invalidate", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Cache invalidate failed: HTTP {response.status_code}")


class QueueThroughputTestUser(HttpUser):
    """Test throughput untuk queue operations"""
    
    wait_time = between(0.01, 0.05)  # Very fast
    
    def on_start(self):
        self.node_id = f"queue_client_{random.randint(1000, 9999)}"
        self.topic = "throughput_test"
    
    @task(10)
    def high_throughput_produce(self):
        """High throughput message production"""
        message = f"msg_{self.node_id}_{int(time.time() * 1000)}"
        
        payload = {
            'topic': self.topic,
            'message': message
        }
        
        with self.client.post("/queue/produce", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Produce failed: HTTP {response.status_code}")
    
    @task(5)
    def high_throughput_consume(self):
        """High throughput message consumption"""
        payload = {'topic': self.topic}
        
        with self.client.post("/queue/consume", 
                             json=payload, 
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Consume failed: HTTP {response.status_code}")
