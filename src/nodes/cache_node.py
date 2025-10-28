import asyncio
import time
from collections import OrderedDict
from enum import Enum

class CacheState(Enum):
    MODIFIED = "M"      # Cache line is modified and dirty
    EXCLUSIVE = "E"     # Cache line is exclusive and clean
    SHARED = "S"        # Cache line is shared and clean
    INVALID = "I"       # Cache line is invalid

class CacheNode:
    def __init__(self, node_id, msg_client=None, capacity=100):
        self.node_id = node_id
        self.msg = msg_client
        self.capacity = capacity
        self.cache = OrderedDict()
        self._lock = asyncio.Lock()
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'invalidations_sent': 0,
            'invalidations_received': 0,
            'state_transitions': 0
        }

    async def start_background(self, app):
        app.loop.create_task(self._metrics_loop())

    async def _metrics_loop(self):
        """Periodically log cache metrics"""
        while True:
            await asyncio.sleep(30)
            print(f"[{self.node_id}] Cache metrics: {self.metrics}")

    async def get(self, key):
        """Read operation - implements MESI protocol"""
        async with self._lock:
            if key in self.cache:
                state, value, timestamp = self.cache.pop(key)
                # Move to end for LRU
                self.cache[key] = (state, value, timestamp)
                
                # MESI state transitions for read
                if state == CacheState.MODIFIED:
                    # M -> M (no change needed)
                    self.metrics['hits'] += 1
                elif state == CacheState.EXCLUSIVE:
                    # E -> S (become shared)
                    self.cache[key] = (CacheState.SHARED, value, timestamp)
                    self.metrics['state_transitions'] += 1
                    self.metrics['hits'] += 1
                elif state == CacheState.SHARED:
                    # S -> S (no change needed)
                    self.metrics['hits'] += 1
                else:  # INVALID
                    # I -> S (need to fetch from other nodes)
                    await self._fetch_from_peers(key)
                    self.metrics['misses'] += 1
                    return None
                
                return value
            else:
                # Cache miss - need to fetch from peers
                await self._fetch_from_peers(key)
                self.metrics['misses'] += 1
                return None

    async def put(self, key, value):
        """Write operation - implements MESI protocol"""
        async with self._lock:
            current_state = CacheState.INVALID
            if key in self.cache:
                current_state, _, _ = self.cache.pop(key)
            
            # MESI state transitions for write
            if current_state == CacheState.MODIFIED:
                # M -> M (update value)
                self.cache[key] = (CacheState.MODIFIED, value, time.time())
            elif current_state == CacheState.EXCLUSIVE:
                # E -> M (become modified)
                self.cache[key] = (CacheState.MODIFIED, value, time.time())
                self.metrics['state_transitions'] += 1
            elif current_state == CacheState.SHARED:
                # S -> M (invalidate other copies first)
                await self._invalidate_peers(key)
                self.cache[key] = (CacheState.MODIFIED, value, time.time())
                self.metrics['state_transitions'] += 1
            else:  # INVALID
                # I -> M (invalidate other copies first)
                await self._invalidate_peers(key)
                self.cache[key] = (CacheState.MODIFIED, value, time.time())
                self.metrics['state_transitions'] += 1
            
            # Apply LRU eviction if needed
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)
            
            return True

    async def _fetch_from_peers(self, key):
        """Fetch data from other cache nodes"""
        if not self.msg:
            return
        
        for peer in self.msg.peers:
            try:
                response = await self.msg.get(peer, f'/cache/fetch?key={key}')
                if response and 'value' in response and response['value'] is not None:
                    # Mark as shared since we got it from another node
                    self.cache[key] = (CacheState.SHARED, response['value'], time.time())
                    break
            except Exception:
                continue

    async def _invalidate_peers(self, key):
        """Send invalidation messages to all peers"""
        if not self.msg:
            return
        
        for peer in self.msg.peers:
            try:
                await self.msg.post(peer, '/cache/invalidate', {'key': key})
                self.metrics['invalidations_sent'] += 1
            except Exception:
                continue

    async def handle_invalidate(self, key):
        """Handle invalidation request from other nodes"""
        async with self._lock:
            if key in self.cache:
                state, value, timestamp = self.cache.pop(key)
                self.metrics['invalidations_received'] += 1
                # State transition: any state -> I
                self.metrics['state_transitions'] += 1

    async def handle_fetch(self, key):
        """Handle fetch request from other nodes"""
        async with self._lock:
            if key in self.cache:
                state, value, timestamp = self.cache.pop(key)
                # Move to end for LRU
                self.cache[key] = (state, value, timestamp)
                
                # State transition based on current state
                if state == CacheState.MODIFIED:
                    # M -> S (downgrade to shared)
                    self.cache[key] = (CacheState.SHARED, value, timestamp)
                    self.metrics['state_transitions'] += 1
                elif state == CacheState.EXCLUSIVE:
                    # E -> S (become shared)
                    self.cache[key] = (CacheState.SHARED, value, timestamp)
                    self.metrics['state_transitions'] += 1
                
                return {'value': value, 'state': state.value}
            return {'value': None}

    async def get_cache_state(self):
        """Get current cache state for monitoring"""
        async with self._lock:
            state_summary = {}
            for key, (state, value, timestamp) in self.cache.items():
                state_summary[key] = {
                    'state': state.value,
                    'age': time.time() - timestamp
                }
            return {
                'cache_state': state_summary,
                'metrics': self.metrics.copy(),
                'capacity_used': len(self.cache),
                'capacity_total': self.capacity
            }
