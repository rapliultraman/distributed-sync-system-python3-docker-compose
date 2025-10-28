import os
CONFIG = {
    'NODE_ID': os.getenv('NODE_ID', 'node1'),
    'PEERS': os.getenv('PEERS', 'node1,node2,node3').split(','),
    'REDIS_URL': os.getenv('REDIS_URL', 'redis://redis:6379/0'),
}
