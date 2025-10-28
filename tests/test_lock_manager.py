import asyncio
from src.consensus.raft_redis import RaftRedis
from src.nodes.lock_manager import LockManager
class DummyMsg:
    async def post(self, *args, **kwargs): return None
    async def get(self, *args, **kwargs): return None

async def test_lock_sequence():
    class FakeRedis:
        def __init__(self):
            self.list = []
        async def rpush(self, k, v):
            self.list.append(v); return len(self.list)
        async def llen(self, k):
            return len(self.list)
        async def lindex(self, k, i):
            return self.list[i]
        async def lrange(self, k, a, b):
            return self.list[a:b+1]
        async def set(self, k, v): pass
    redis = FakeRedis()
    raft = RaftRedis('node1',['node2'], redis=redis, msg_client=DummyMsg())
    lm = LockManager('node1', raft, msg_client=DummyMsg())
    raft.leader = 'node1'
    await raft.append_command({'type':'acquire','resource':'r1','owner':'a','mode':'exclusive'})
    await lm._apply_acquire('r1','a','exclusive')
    assert 'a' in lm.locks['r1']['holders']
