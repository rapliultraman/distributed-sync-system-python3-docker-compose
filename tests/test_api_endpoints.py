import pytest
import asyncio
import json
from aiohttp import web, ClientSession
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from src.api.handlers import Handlers
from src.api.endpoints import register_routes
from src.nodes.base_node import create_app

class TestAPIEndpoints(AioHTTPTestCase):
    """Test suite untuk API endpoints"""
    
    async def get_application(self):
        """Setup test application"""
        app = web.Application()
        
        # Mock components
        app['node_id'] = 'test_node'
        app['raft'] = MockRaft()
        app['lockman'] = MockLockManager()
        app['queue'] = MockQueue()
        app['cache'] = MockCache()
        app['metrics'] = MockMetrics()
        app['logger'] = MockLogger()
        app['error_handler'] = MockErrorHandler()
        
        await register_routes(app)
        return app
    
    @unittest_run_loop
    async def test_health_endpoint(self):
        """Test health endpoint"""
        resp = await self.client.request('GET', '/health')
        assert resp.status == 200
        
        data = await resp.json()
        assert data['status'] == 'ok'
        assert data['node_id'] == 'test_node'
    
    @unittest_run_loop
    async def test_leader_endpoint(self):
        """Test leader endpoint"""
        resp = await self.client.request('GET', '/raft/leader')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'leader' in data
        assert 'term' in data
    
    @unittest_run_loop
    async def test_heartbeat_endpoint(self):
        """Test heartbeat endpoint"""
        payload = {'leader': 'test_leader', 'term': 1}
        resp = await self.client.request('POST', '/raft/heartbeat', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert data['status'] == 'ok'
    
    @unittest_run_loop
    async def test_append_endpoint(self):
        """Test append endpoint"""
        payload = {'type': 'test', 'data': 'test_data'}
        resp = await self.client.request('POST', '/raft/append', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert data['status'] == 'ok'
        assert 'index' in data
    
    @unittest_run_loop
    async def test_get_log_endpoint(self):
        """Test get log endpoint"""
        resp = await self.client.request('GET', '/raft/log')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'log' in data
    
    @unittest_run_loop
    async def test_acquire_lock_endpoint(self):
        """Test acquire lock endpoint"""
        payload = {'resource': 'test_resource', 'owner': 'test_owner', 'mode': 'exclusive'}
        resp = await self.client.request('POST', '/locks/acquire', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert 'success' in data
    
    @unittest_run_loop
    async def test_release_lock_endpoint(self):
        """Test release lock endpoint"""
        payload = {'resource': 'test_resource', 'owner': 'test_owner'}
        resp = await self.client.request('POST', '/locks/release', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert 'success' in data
    
    @unittest_run_loop
    async def test_wait_for_endpoint(self):
        """Test wait-for endpoint"""
        resp = await self.client.request('GET', '/locks/wait_for')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'edges' in data
    
    @unittest_run_loop
    async def test_produce_endpoint(self):
        """Test produce endpoint"""
        payload = {'topic': 'test_topic', 'message': 'test_message'}
        resp = await self.client.request('POST', '/queue/produce', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert data['status'] == 'ok'
    
    @unittest_run_loop
    async def test_consume_endpoint(self):
        """Test consume endpoint"""
        payload = {'topic': 'test_topic'}
        resp = await self.client.request('POST', '/queue/consume', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert 'message' in data
    
    @unittest_run_loop
    async def test_cache_get_endpoint(self):
        """Test cache get endpoint"""
        resp = await self.client.request('GET', '/cache/get?key=test_key')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'value' in data
    
    @unittest_run_loop
    async def test_cache_put_endpoint(self):
        """Test cache put endpoint"""
        payload = {'key': 'test_key', 'value': 'test_value'}
        resp = await self.client.request('POST', '/cache/put', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert 'success' in data
    
    @unittest_run_loop
    async def test_cache_invalidate_endpoint(self):
        """Test cache invalidate endpoint"""
        payload = {'key': 'test_key'}
        resp = await self.client.request('POST', '/cache/invalidate', json=payload)
        assert resp.status == 200
        
        data = await resp.json()
        assert data['status'] == 'ok'
    
    @unittest_run_loop
    async def test_cache_fetch_endpoint(self):
        """Test cache fetch endpoint"""
        resp = await self.client.request('GET', '/cache/fetch?key=test_key')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'value' in data
    
    @unittest_run_loop
    async def test_cache_state_endpoint(self):
        """Test cache state endpoint"""
        resp = await self.client.request('GET', '/cache/state')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'cache_state' in data
        assert 'metrics' in data
    
    @unittest_run_loop
    async def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        resp = await self.client.request('GET', '/metrics')
        assert resp.status == 200
        
        data = await resp.json()
        assert 'node_id' in data
        assert 'uptime_seconds' in data
    
    @unittest_run_loop
    async def test_metrics_prometheus_format(self):
        """Test metrics endpoint with Prometheus format"""
        resp = await self.client.request('GET', '/metrics?format=prometheus')
        assert resp.status == 200
        assert resp.content_type == 'text/plain; version=0.0.4; charset=utf-8'
    
    @unittest_run_loop
    async def test_invalid_endpoints(self):
        """Test invalid endpoint requests"""
        # Missing required fields
        resp = await self.client.request('POST', '/locks/acquire', json={})
        assert resp.status == 400
        
        resp = await self.client.request('POST', '/queue/produce', json={})
        assert resp.status == 400
        
        resp = await self.client.request('GET', '/cache/get')
        assert resp.status == 400

# Mock classes untuk testing
class MockRaft:
    def __init__(self):
        self.leader = 'test_node'
        self.term = 1
    
    async def receive_heartbeat(self, data):
        pass
    
    async def append_command(self, data):
        return 0
    
    async def get_log(self, start=0, end=-1):
        return []

class MockLockManager:
    def __init__(self):
        pass
    
    async def acquire(self, resource, owner, mode='shared'):
        return True
    
    async def release(self, resource, owner):
        return True
    
    def local_wait_for_edges(self):
        return []

class MockQueue:
    def __init__(self):
        pass
    
    async def produce(self, topic, message):
        pass
    
    async def consume(self, topic):
        return "test_message"

class MockCache:
    def __init__(self):
        pass
    
    async def get(self, key):
        return "test_value"
    
    async def put(self, key, value):
        return True
    
    async def handle_invalidate(self, key):
        pass
    
    async def handle_fetch(self, key):
        return {'value': 'test_value', 'state': 'S'}
    
    async def get_cache_state(self):
        return {
            'cache_state': {},
            'metrics': {'hits': 0, 'misses': 0},
            'capacity_used': 0,
            'capacity_total': 100
        }

class MockMetrics:
    def __init__(self):
        pass
    
    def get_metrics_endpoint_data(self):
        return {
            'prometheus_format': '# HELP test_metric Test metric\n# TYPE test_metric counter\ntest_metric 1',
            'json_format': {
                'node_id': 'test_node',
                'uptime_seconds': 100.0,
                'counters': {},
                'gauges': {},
                'histograms': {}
            }
        }

class MockLogger:
    def __init__(self):
        pass
    
    def info(self, message, **kwargs):
        pass
    
    def error(self, message, **kwargs):
        pass
    
    def debug(self, message, **kwargs):
        pass

class MockErrorHandler:
    def __init__(self):
        pass
    
    def handle_error(self, operation, error, context=None):
        pass

# Performance tests
class TestAPIPerformance:
    """Performance tests untuk API endpoints"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent API requests"""
        async def make_request(session, url, data):
            async with session.post(url, json=data) as resp:
                return await resp.json()
        
        async with ClientSession() as session:
            tasks = []
            for i in range(10):
                task = make_request(
                    session, 
                    'http://localhost:8001/locks/acquire',
                    {'resource': f'resource_{i}', 'owner': f'client_{i}', 'mode': 'exclusive'}
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            assert len(results) == 10
            assert all('success' in result for result in results)
    
    @pytest.mark.asyncio
    async def test_high_frequency_requests(self):
        """Test high frequency API requests"""
        async def make_health_request(session):
            async with session.get('http://localhost:8001/health') as resp:
                return resp.status
        
        async with ClientSession() as session:
            start_time = asyncio.get_event_loop().time()
            
            tasks = []
            for _ in range(100):
                task = make_health_request(session)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            end_time = asyncio.get_event_loop().time()
            
            duration = end_time - start_time
            requests_per_second = 100 / duration
            
            assert all(status == 200 for status in results)
            assert requests_per_second > 50  # At least 50 RPS

# Test configuration
pytestmark = pytest.mark.asyncio
