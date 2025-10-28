Architecture overview:
- 3 nodes (node1, node2, node3) as aiohttp services
- RaftRedis: leader election + redis-backed log
- LockManager sequences via log entries
- Queue uses Redis lists
- Cache invalidation via HTTP broadcast
