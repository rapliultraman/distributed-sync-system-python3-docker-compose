import asyncio, json, time
from typing import Dict, List, Tuple
class LockManager:
    def __init__(self, node_id, raft, msg_client=None):
        self.node_id = node_id
        self.raft = raft
        self.msg = msg_client
        self.locks: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self._last_applied = -1

    async def start_background(self, app):
        app.loop.create_task(self._apply_loop())
        app.loop.create_task(self._deadlock_loop())

    async def _apply_loop(self):
        while True:
            if not self.raft.redis:
                await asyncio.sleep(1.0)
                continue
            length = await self.raft.redis.llen('raft:log')
            while self._last_applied < length-1:
                self._last_applied += 1
                entry = await self.raft.redis.lindex('raft:log', self._last_applied)
                try:
                    obj = json.loads(entry)
                    cmd = obj.get('cmd', {})
                    typ = cmd.get('type')
                    if typ == 'acquire':
                        await self._apply_acquire(cmd['resource'], cmd['owner'], cmd['mode'])
                    elif typ == 'release':
                        await self._apply_release(cmd['resource'], cmd['owner'])
                except Exception as e:
                    print('apply error', e)
            await asyncio.sleep(0.2)

    async def _apply_acquire(self, resource, owner, mode):
        async with self._lock:
            info = self.locks.setdefault(resource, {'mode': None, 'holders': set(), 'queue': []})
            if not info['holders']:
                info['mode'] = mode
                info['holders'].add(owner)
            elif mode == 'shared' and info['mode'] == 'shared':
                info['holders'].add(owner)
            else:
                if (owner, mode) not in info['queue']:
                    info['queue'].append((owner, mode))

    async def _apply_release(self, resource, owner):
        async with self._lock:
            info = self.locks.get(resource)
            if not info: return
            if owner in info['holders']:
                info['holders'].remove(owner)
            if not info['holders']:
                if info['queue']:
                    next_owner, next_mode = info['queue'].pop(0)
                    info['mode'] = next_mode
                    info['holders'].add(next_owner)
                else:
                    info['mode'] = None

    async def acquire(self, resource: str, owner: str, mode: str='shared'):
        if self.raft.leader != self.node_id:
            if self.raft.leader and self.msg:
                try:
                    await self.msg.post(self.raft.leader, '/raft/append', {'type':'acquire','resource':resource,'owner':owner,'mode':mode})
                    return True
                except Exception:
                    pass
            return False
        else:
            idx = await self.raft.append_command({'type':'acquire','resource':resource,'owner':owner,'mode':mode})
            return True

    async def release(self, resource: str, owner: str):
        if self.raft.leader != self.node_id:
            if self.raft.leader and self.msg:
                await self.msg.post(self.raft.leader, '/raft/append', {'type':'release','resource':resource,'owner':owner})
                return True
            return False
        else:
            await self.raft.append_command({'type':'release','resource':resource,'owner':owner})
            return True

    async def _deadlock_loop(self):
        while True:
            await asyncio.sleep(5)
            if self.raft.leader == self.node_id and self.msg:
                edges = []
                for peer in self.raft.peers + [self.node_id]:
                    try:
                        res = await self.msg.get(peer, '/locks/wait_for')
                        if res and 'edges' in res:
                            edges.extend(res['edges'])
                    except Exception:
                        pass
                cycle = self._detect_cycle(edges)
                if cycle:
                    victim = cycle[0]
                    for r, info in list(self.locks.items()):
                        if victim in info.get('holders', set()):
                            print('Deadlock detected. Leader aborting', victim, 'on', r)
                            await self.raft.append_command({'type':'release','resource':r,'owner':victim})
                            break

    def local_wait_for_edges(self):
        edges = []
        for r, info in self.locks.items():
            queue = info.get('queue', [])
            holders = info.get('holders', set())
            for waiting, mode in queue:
                for h in holders:
                    edges.append((waiting, h))
        return edges

    def _detect_cycle(self, edges):
        graph = {}
        for a,b in edges:
            graph.setdefault(a, []).append(b)
        visited = set()
        stack = []
        def dfs(n):
            if n in stack:
                idx = stack.index(n)
                return stack[idx:]
            if n in visited:
                return None
            visited.add(n)
            stack.append(n)
            for nb in graph.get(n,[]):
                cyc = dfs(nb)
                if cyc:
                    return cyc
            stack.pop()
            return None
        for node in graph.keys():
            cyc = dfs(node)
            if cyc:
                return cyc
        return None
