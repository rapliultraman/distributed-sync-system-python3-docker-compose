import asyncio, time, json

class RaftRedis:
    """
    Simplified Raft-like leader election with Redis-backed log.
    This is an educational implementation: leader appends commands to Redis list 'raft:log';
    followers tail the list and apply entries. Heartbeat is broadcast via HTTP to peers.
    """
    def __init__(self, node_id, peers, redis=None, msg_client=None):
        self.node_id = node_id
        self.peers = [p for p in peers if p != node_id]
        self.redis = redis
        self.msg = msg_client
        self.leader = None
        self.term = 0
        self.last_heartbeat = 0
        self.apply_index = -1
        self._lock = asyncio.Lock()

    async def start_background(self, app):
        app.loop.create_task(self._heartbeat_loop())
        app.loop.create_task(self._tail_log_loop())

    async def _heartbeat_loop(self):
        while True:
            now = time.time()
            if self.leader is None or (now - self.last_heartbeat) > 3.0:
                async with self._lock:
                    self.term += 1
                    self.leader = self.node_id
                    self.last_heartbeat = time.time()
                if self.msg:
                    for p in self.peers:
                        try:
                            await self.msg.post(p, '/raft/heartbeat', {'leader': self.leader, 'term': self.term})
                        except Exception:
                            pass
            await asyncio.sleep(1.0)

    async def receive_heartbeat(self, data):
        leader = data.get('leader')
        term = data.get('term', 0)
        if term >= self.term:
            self.leader = leader
            self.term = term
            self.last_heartbeat = time.time()

    async def append_command(self, command: dict):
        if not self.redis:
            raise RuntimeError("Redis not configured for log")
        async with self._lock:
            entry = json.dumps({'term': self.term, 'cmd': command, 'ts': time.time()})
            idx = await self.redis.rpush('raft:log', entry)
            return idx-1

    async def get_log(self, start=0, end=-1):
        if not self.redis:
            return []
        lst = await self.redis.lrange('raft:log', start, end)
        return lst

    async def _tail_log_loop(self):
        if not self.redis:
            return
        while True:
            try:
                length = await self.redis.llen('raft:log')
                while self.apply_index < length-1:
                    self.apply_index += 1
                    entry = await self.redis.lindex('raft:log', self.apply_index)
                    await self.redis.set(f'raft:applied:{self.node_id}', self.apply_index)
                await asyncio.sleep(0.5)
            except Exception:
                await asyncio.sleep(1.0)
