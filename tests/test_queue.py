import pytest
from src.nodes.queue_node import DistributedQueue

@pytest.mark.asyncio
async def test_queue_fallback(tmp_path):
    q = DistributedQueue('n1', redis_client=None)
    topic = 't1'
    await q.produce(topic, 'm1')
    await q.produce(topic, 'm2')
    m = await q.consume(topic)
    assert m == 'm1'
    m2 = await q.consume(topic)
    assert m2 == 'm2'
