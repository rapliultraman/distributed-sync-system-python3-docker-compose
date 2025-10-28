import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch
from src.consensus.raft_redis import RaftRedis
from src.nodes.lock_manager import LockManager
from src.nodes.queue_node import DistributedQueue
from src.nodes.cache_node import CacheNode, CacheState
from src.communication.message_passing import MessageClient
from src.utils.metrics import MetricsCollector, SystemMetrics
from src.utils.logging import DistributedSystemLogger

class TestRaftRedis:
    """Test suite untuk Raft Redis consensus"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis = Mock()
        redis.rpush = AsyncMock(return_value=1)
        redis.lrange = AsyncMock(return_value=[])
        redis.llen = AsyncMock(return_value=0)
        redis.lindex = AsyncMock(return_value=None)
        redis.set = AsyncMock()
        return redis
    
    @pytest.fixture
    def mock_msg_client(self):
        """Mock message client"""
        msg_client = Mock()
        msg_client.post = AsyncMock()
        msg_client.get = AsyncMock()
        return msg_client
    
    @pytest.fixture
    def raft_instance(self, mock_redis, mock_msg_client):
        """Raft instance untuk testing"""
        return RaftRedis(
            node_id="test_node",
            peers=["peer1", "peer2"],
            redis=mock_redis,
            msg_client=mock_msg_client
        )
    
    @pytest.mark.asyncio
    async def test_raft_initialization(self, raft_instance):
        """Test Raft initialization"""
        assert raft_instance.node_id == "test_node"
        assert raft_instance.peers == ["peer1", "peer2"]
        assert raft_instance.leader is None
        assert raft_instance.term == 0
    
    @pytest.mark.asyncio
    async def test_append_command(self, raft_instance, mock_redis):
        """Test append command to log"""
        raft_instance.leader = "test_node"
        raft_instance.term = 1
        
        command = {"type": "test", "data": "test_data"}
        result = await raft_instance.append_command(command)
        
        assert result == 0  # rpush returns length, index is length-1
        mock_redis.rpush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_receive_heartbeat(self, raft_instance):
        """Test receive heartbeat"""
        heartbeat_data = {"leader": "peer1", "term": 2}
        
        await raft_instance.receive_heartbeat(heartbeat_data)
        
        assert raft_instance.leader == "peer1"
        assert raft_instance.term == 2
    
    @pytest.mark.asyncio
    async def test_get_log(self, raft_instance, mock_redis):
        """Test get log entries"""
        mock_redis.lrange.return_value = ['{"term": 1, "cmd": {"type": "test"}}']
        
        log = await raft_instance.get_log()
        
        assert len(log) == 1
        mock_redis.lrange.assert_called_once_with('raft:log', 0, -1)

class TestLockManager:
    """Test suite untuk Lock Manager"""
    
    @pytest.fixture
    def mock_raft(self):
        """Mock Raft instance"""
        raft = Mock()
        raft.leader = "test_node"
        raft.node_id = "test_node"
        raft.append_command = AsyncMock(return_value=0)
        raft.redis = Mock()
        raft.redis.llen = AsyncMock(return_value=0)
        raft.redis.lindex = AsyncMock(return_value=None)
        raft.peers = ["peer1", "peer2"]
        return raft
    
    @pytest.fixture
    def mock_msg_client(self):
        """Mock message client"""
        msg_client = Mock()
        msg_client.post = AsyncMock()
        msg_client.get = AsyncMock()
        return msg_client
    
    @pytest.fixture
    def lock_manager(self, mock_raft, mock_msg_client):
        """Lock manager instance untuk testing"""
        return LockManager(
            node_id="test_node",
            raft=mock_raft,
            msg_client=mock_msg_client
        )
    
    @pytest.mark.asyncio
    async def test_lock_manager_initialization(self, lock_manager):
        """Test lock manager initialization"""
        assert lock_manager.node_id == "test_node"
        assert lock_manager.locks == {}
    
    @pytest.mark.asyncio
    async def test_acquire_lock_as_leader(self, lock_manager, mock_raft):
        """Test acquire lock as leader"""
        result = await lock_manager.acquire("resource1", "client1", "exclusive")
        
        assert result is True
        mock_raft.append_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_acquire_lock_as_follower(self, lock_manager, mock_raft, mock_msg_client):
        """Test acquire lock as follower"""
        mock_raft.leader = "peer1"
        
        result = await lock_manager.acquire("resource1", "client1", "exclusive")
        
        assert result is True
        mock_msg_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_acquire(self, lock_manager):
        """Test apply acquire operation"""
        await lock_manager._apply_acquire("resource1", "client1", "exclusive")
        
        assert "resource1" in lock_manager.locks
        assert "client1" in lock_manager.locks["resource1"]["holders"]
        assert lock_manager.locks["resource1"]["mode"] == "exclusive"
    
    @pytest.mark.asyncio
    async def test_apply_release(self, lock_manager):
        """Test apply release operation"""
        # First acquire
        await lock_manager._apply_acquire("resource1", "client1", "exclusive")
        
        # Then release
        await lock_manager._apply_release("resource1", "client1")
        
        assert "client1" not in lock_manager.locks["resource1"]["holders"]
        assert lock_manager.locks["resource1"]["mode"] is None
    
    @pytest.mark.asyncio
    async def test_shared_lock_acquisition(self, lock_manager):
        """Test shared lock acquisition"""
        # First client acquires shared lock
        await lock_manager._apply_acquire("resource1", "client1", "shared")
        
        # Second client acquires shared lock
        await lock_manager._apply_acquire("resource1", "client2", "shared")
        
        assert "client1" in lock_manager.locks["resource1"]["holders"]
        assert "client2" in lock_manager.locks["resource1"]["holders"]
        assert lock_manager.locks["resource1"]["mode"] == "shared"
    
    @pytest.mark.asyncio
    async def test_exclusive_lock_queue(self, lock_manager):
        """Test exclusive lock queuing"""
        # First client acquires exclusive lock
        await lock_manager._apply_acquire("resource1", "client1", "exclusive")
        
        # Second client tries to acquire exclusive lock
        await lock_manager._apply_acquire("resource1", "client2", "exclusive")
        
        assert "client2" not in lock_manager.locks["resource1"]["holders"]
        assert ("client2", "exclusive") in lock_manager.locks["resource1"]["queue"]
    
    def test_local_wait_for_edges(self, lock_manager):
        """Test wait-for graph generation"""
        # Setup locks with waiting clients
        lock_manager.locks["resource1"] = {
            "mode": "exclusive",
            "holders": {"client1"},
            "queue": [("client2", "exclusive")]
        }
        
        edges = lock_manager.local_wait_for_edges()
        
        assert ("client2", "client1") in edges
    
    def test_cycle_detection(self, lock_manager):
        """Test cycle detection algorithm"""
        edges = [("client1", "client2"), ("client2", "client3"), ("client3", "client1")]
        
        cycle = lock_manager._detect_cycle(edges)
        
        assert cycle is not None
        assert len(cycle) > 0

class TestDistributedQueue:
    """Test suite untuk Distributed Queue"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis = Mock()
        redis.rpush = AsyncMock(return_value=1)
        redis.lpop = AsyncMock(return_value="test_message")
        return redis
    
    @pytest.fixture
    def queue_instance(self, mock_redis):
        """Queue instance untuk testing"""
        return DistributedQueue(node_id="test_node", redis_client=mock_redis)
    
    @pytest.mark.asyncio
    async def test_queue_initialization(self, queue_instance):
        """Test queue initialization"""
        assert queue_instance.node_id == "test_node"
        assert queue_instance.redis is not None
    
    @pytest.mark.asyncio
    async def test_produce_message(self, queue_instance, mock_redis):
        """Test produce message"""
        await queue_instance.produce("test_topic", "test_message")
        
        mock_redis.rpush.assert_called_once_with("queue:test_topic", "test_message")
    
    @pytest.mark.asyncio
    async def test_consume_message(self, queue_instance, mock_redis):
        """Test consume message"""
        result = await queue_instance.consume("test_topic")
        
        assert result == "test_message"
        mock_redis.lpop.assert_called_once_with("queue:test_topic")
    
    @pytest.mark.asyncio
    async def test_consume_empty_queue(self, queue_instance, mock_redis):
        """Test consume from empty queue"""
        mock_redis.lpop.return_value = None
        
        result = await queue_instance.consume("test_topic")
        
        assert result is None

class TestCacheNode:
    """Test suite untuk Cache Node dengan MESI Protocol"""
    
    @pytest.fixture
    def mock_msg_client(self):
        """Mock message client"""
        msg_client = Mock()
        msg_client.post = AsyncMock()
        msg_client.get = AsyncMock()
        msg_client.peers = ["peer1", "peer2"]
        return msg_client
    
    @pytest.fixture
    def cache_instance(self, mock_msg_client):
        """Cache instance untuk testing"""
        return CacheNode(node_id="test_node", msg_client=mock_msg_client, capacity=10)
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, cache_instance):
        """Test cache initialization"""
        assert cache_instance.node_id == "test_node"
        assert cache_instance.capacity == 10
        assert cache_instance.cache == {}
        assert cache_instance.metrics['hits'] == 0
    
    @pytest.mark.asyncio
    async def test_cache_put_modified_state(self, cache_instance):
        """Test cache put operation - Modified state"""
        await cache_instance.put("key1", "value1")
        
        assert "key1" in cache_instance.cache
        state, value, timestamp = cache_instance.cache["key1"]
        assert state == CacheState.MODIFIED
        assert value == "value1"
    
    @pytest.mark.asyncio
    async def test_cache_get_hit(self, cache_instance):
        """Test cache get operation - hit"""
        await cache_instance.put("key1", "value1")
        
        result = await cache_instance.get("key1")
        
        assert result == "value1"
        assert cache_instance.metrics['hits'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_get_miss(self, cache_instance):
        """Test cache get operation - miss"""
        result = await cache_instance.get("nonexistent_key")
        
        assert result is None
        assert cache_instance.metrics['misses'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache_instance):
        """Test cache invalidation"""
        await cache_instance.put("key1", "value1")
        await cache_instance.handle_invalidate("key1")
        
        assert "key1" not in cache_instance.cache
        assert cache_instance.metrics['invalidations_received'] == 1
    
    @pytest.mark.asyncio
    async def test_cache_fetch_from_peer(self, cache_instance, mock_msg_client):
        """Test cache fetch from peer"""
        mock_msg_client.get.return_value = {"value": "peer_value"}
        
        await cache_instance._fetch_from_peers("key1")
        
        assert "key1" in cache_instance.cache
        state, value, timestamp = cache_instance.cache["key1"]
        assert state == CacheState.SHARED
        assert value == "peer_value"
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self, cache_instance):
        """Test LRU eviction when capacity exceeded"""
        # Fill cache to capacity
        for i in range(10):
            await cache_instance.put(f"key{i}", f"value{i}")
        
        # Add one more item to trigger eviction
        await cache_instance.put("key10", "value10")
        
        assert len(cache_instance.cache) == 10
        assert "key0" not in cache_instance.cache  # First item evicted
        assert "key10" in cache_instance.cache  # New item added
    
    @pytest.mark.asyncio
    async def test_cache_state_transitions(self, cache_instance):
        """Test MESI state transitions"""
        # Initial put - should be Modified
        await cache_instance.put("key1", "value1")
        state, _, _ = cache_instance.cache["key1"]
        assert state == CacheState.MODIFIED
        
        # Get from same node - should stay Modified
        await cache_instance.get("key1")
        state, _, _ = cache_instance.cache["key1"]
        assert state == CacheState.MODIFIED
        
        # Handle fetch from peer - should become Shared
        await cache_instance.handle_fetch("key1")
        state, _, _ = cache_instance.cache["key1"]
        assert state == CacheState.SHARED

class TestMessageClient:
    """Test suite untuk Message Client"""
    
    @pytest.fixture
    def message_client(self):
        """Message client instance untuk testing"""
        # Gunakan nama node yang sesuai dengan format (node1, node2, dst)
        return MessageClient(node_id="node1", peers=["node2", "node3"])
    
    def test_message_client_initialization(self, message_client):
        """Test message client initialization"""
        assert message_client.node_id == "node1"
        assert message_client.peers == ["node2", "node3"]
    
    def test_url_generation_docker_env(self, message_client):
        """Test URL generation in Docker environment"""
        with patch.dict('os.environ', {'DOCKER_ENV': '1'}):
            url = message_client._url("node2", "/test")
            assert url == "http://node2:8002/test"
    
    def test_url_generation_local_env(self, message_client):
        """Test URL generation in local environment"""
        with patch.dict('os.environ', {}, clear=True):
            url = message_client._url("node2", "/test")
            assert url == "http://localhost:8002/test"

class TestMetricsCollector:
    """Test suite untuk Metrics Collector"""
    
    @pytest.fixture
    def metrics_collector(self):
        """Metrics collector instance untuk testing"""
        return MetricsCollector("test_node")
    
    def test_metrics_initialization(self, metrics_collector):
        """Test metrics collector initialization"""
        assert metrics_collector.node_id == "test_node"
        assert metrics_collector.metrics == {}
        assert metrics_collector.counters == {}
    
    def test_increment_counter(self, metrics_collector):
        """Test counter increment"""
        metrics_collector.increment_counter("test_counter", 5)
        
        assert metrics_collector.counters["test_counter"] == 5
    
    def test_set_gauge(self, metrics_collector):
        """Test gauge setting"""
        metrics_collector.set_gauge("test_gauge", 42.5)
        
        assert metrics_collector.metrics['gauge']["test_gauge"] == 42.5
    
    def test_record_histogram(self, metrics_collector):
        """Test histogram recording"""
        metrics_collector.record_histogram("test_histogram", 1.5)
        metrics_collector.record_histogram("test_histogram", 2.5)
        metrics_collector.record_histogram("test_histogram", 3.5)
        
        values = metrics_collector.histograms["test_histogram"]
        assert len(values) == 3
        assert 1.5 in values
        assert 2.5 in values
        assert 3.5 in values
    
    def test_get_metrics_summary(self, metrics_collector):
        """Test metrics summary generation"""
        metrics_collector.increment_counter("test_counter", 10)
        metrics_collector.set_gauge("test_gauge", 100.0)
        metrics_collector.record_histogram("test_histogram", 1.0)
        metrics_collector.record_histogram("test_histogram", 2.0)
        
        summary = metrics_collector.get_metrics_summary()
        
        assert summary['node_id'] == "test_node"
        assert summary['counters']['test_counter'] == 10
        assert summary['gauges']['test_gauge'] == 100.0
        assert 'test_histogram' in summary['histograms']
        assert summary['histograms']['test_histogram']['count'] == 2

class TestSystemMetrics:
    """Test suite untuk System Metrics"""
    
    @pytest.fixture
    def system_metrics(self):
        """System metrics instance untuk testing"""
        return SystemMetrics("test_node")
    
    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, system_metrics):
        """Test system metrics collection"""
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.net_io_counters') as mock_network:
            
            mock_memory.return_value.percent = 60.0
            mock_memory.return_value.available = 1024 * 1024 * 1024  # 1GB
            mock_disk.return_value.percent = 70.0
            mock_disk.return_value.free = 2 * 1024 * 1024 * 1024  # 2GB
            mock_network.return_value.bytes_sent = 1000
            mock_network.return_value.bytes_recv = 2000
            
            await system_metrics.collect_system_metrics()
            
            assert system_metrics.metrics.metrics['gauge']['cpu_usage_percent'] == 50.0
            assert system_metrics.metrics.metrics['gauge']['memory_usage_percent'] == 60.0
            assert system_metrics.metrics.metrics['gauge']['disk_usage_percent'] == 70.0

class TestIntegration:
    """Integration tests untuk seluruh sistem"""
    
    @pytest.mark.asyncio
    async def test_full_lock_workflow(self):
        """Test complete lock workflow"""
        # Setup components
        mock_redis = Mock()
        mock_redis.rpush = AsyncMock(return_value=1)
        mock_redis.llen = AsyncMock(return_value=1)
        mock_redis.lindex = AsyncMock(return_value='{"term": 1, "cmd": {"type": "acquire", "resource": "r1", "owner": "c1", "mode": "exclusive"}}')
        
        mock_msg_client = Mock()
        mock_msg_client.post = AsyncMock()
        
        raft = RaftRedis("node1", ["node2"], mock_redis, mock_msg_client)
        raft.leader = "node1"
        
        lock_manager = LockManager("node1", raft, mock_msg_client)
        
        # Test lock acquisition
        result = await lock_manager.acquire("resource1", "client1", "exclusive")
        assert result is True
        
        # Test lock release
        result = await lock_manager.release("resource1", "client1")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_cache_coherence_workflow(self):
        """Test cache coherence workflow"""
        mock_msg_client = Mock()
        mock_msg_client.post = AsyncMock()
        mock_msg_client.peers = ["peer1"]
        
        cache1 = CacheNode("node1", mock_msg_client)
        cache2 = CacheNode("node2", mock_msg_client)
        
        # Node1 puts data
        await cache1.put("key1", "value1")
        
        # Node2 should receive invalidation
        await cache2.handle_invalidate("key1")
        
        # Verify invalidation was sent
        mock_msg_client.post.assert_called()
    
    @pytest.mark.asyncio
    async def test_queue_workflow(self):
        """Test queue workflow"""
        mock_redis = Mock()
        mock_redis.rpush = AsyncMock(return_value=1)
        mock_redis.lpop = AsyncMock(return_value="test_message")
        
        queue = DistributedQueue("node1", mock_redis)
        
        # Produce message
        await queue.produce("topic1", "test_message")
        
        # Consume message
        message = await queue.consume("topic1")
        
        assert message == "test_message"

# Test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Test markers
# pytestmark = pytest.mark.asyncio
