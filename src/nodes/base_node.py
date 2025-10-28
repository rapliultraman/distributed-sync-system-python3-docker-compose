import os, asyncio
from aiohttp import web
from src.consensus.raft_redis import RaftRedis
from src.nodes.lock_manager import LockManager
from src.nodes.queue_node import DistributedQueue
from src.nodes.cache_node import CacheNode
from src.utils.metrics import SystemMetrics
from src.utils.logging import setup_logging, get_logger, get_error_handler
from src.communication.message_passing import MessageClient
import redis.asyncio as redis

NODE_ID = os.getenv('NODE_ID', 'node1')
PEERS = os.getenv('PEERS', 'node1,node2,node3').split(',')
HTTP_PORT = int(os.getenv('HTTP_PORT', '8000'))
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

async def create_app():
    # Setup logging first
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    setup_logging(NODE_ID, log_level)
    logger = get_logger(NODE_ID)
    error_handler = get_error_handler()
    
    logger.info("Starting distributed sync system node", node_id=NODE_ID, peers=PEERS)
    
    app = web.Application()
    redis_client = None
    try:
        redis_client = redis.from_url(
            REDIS_URL, 
            encoding='utf-8', 
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        logger.info("Redis connection established", redis_url=REDIS_URL)
    except Exception as e:
        logger.error("Redis connection failed", exception=e, redis_url=REDIS_URL)
        error_handler.handle_error("redis_connection", e, {"redis_url": REDIS_URL})

    msg_client = MessageClient(node_id=NODE_ID, peers=PEERS)
    raft = RaftRedis(node_id=NODE_ID, peers=PEERS, redis=redis_client, msg_client=msg_client)
    lockman = LockManager(node_id=NODE_ID, raft=raft, msg_client=msg_client)
    queue = DistributedQueue(node_id=NODE_ID, redis_client=redis_client)
    cache = CacheNode(node_id=NODE_ID, msg_client=msg_client)
    metrics = SystemMetrics(node_id=NODE_ID)

    app['node_id'] = NODE_ID
    app['raft'] = raft
    app['lockman'] = lockman
    app['queue'] = queue
    app['cache'] = cache
    app['redis'] = redis_client
    app['metrics'] = metrics
    app['logger'] = logger
    app['error_handler'] = error_handler

    logger.info("All components initialized successfully")

    from src.api.endpoints import register_routes
    await register_routes(app)

    app.on_startup.append(lambda a: raft.start_background(a))
    app.on_startup.append(lambda a: lockman.start_background(a))
    app.on_startup.append(lambda a: cache.start_background(a))
    app.on_startup.append(lambda a: metrics.start_background(a))
    
    logger.info("Background tasks started")
    return app

if __name__ == '__main__':
    web.run_app(asyncio.run(create_app()), port=HTTP_PORT)
