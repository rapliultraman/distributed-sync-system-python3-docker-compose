from aiohttp import web
import json
from src.utils.logging import get_logger, get_error_handler

class Handlers:
    def __init__(self, app):
        self.app = app
        self.logger = get_logger(app.get('node_id', 'unknown'))
        self.error_handler = get_error_handler()

    async def _handle_request(self, request_name: str, handler_func, *args, **kwargs):
        """Wrapper untuk handle request dengan error handling dan logging"""
        try:
            self.logger.debug(f"Handling {request_name} request", 
                           method=request.method if hasattr(request, 'method') else 'unknown',
                           path=request.path if hasattr(request, 'path') else 'unknown')
            
            result = await handler_func(*args, **kwargs)
            
            self.logger.debug(f"{request_name} request completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Error handling {request_name} request", exception=e)
            self.error_handler.handle_error(request_name, e)
            
            return web.json_response(
                {'error': f'Internal server error in {request_name}'}, 
                status=500
            )

    async def health(self, request):
        try:
            return web.json_response({
                'status': 'ok',
                'node_id': self.app['node_id'],
                'leader': self.app['raft'].leader,
                'term': self.app['raft'].term
            })
        except Exception as e:
            self.logger.error("Health check failed", exception=e)
            return web.json_response({'status': 'error', 'error': str(e)}, status=500)

    async def leader(self, request):
        raft = self.app['raft']
        return web.json_response({'leader': raft.leader, 'term': raft.term})

    async def heartbeat(self, request):
        data = await request.json()
        await self.app['raft'].receive_heartbeat(data)
        return web.json_response({'status': 'ok'})

    async def append(self, request):
        data = await request.json()
        if self.app['raft'].leader == self.app['node_id']:
            idx = await self.app['raft'].append_command(data)
            return web.json_response({'status': 'ok', 'index': idx})
        else:
            return web.json_response({'error': 'not leader'}, status=403)

    async def get_log(self, request):
        start = int(request.query.get('start', 0))
        end = int(request.query.get('end', -1))
        log = await self.app['raft'].get_log(start, end)
        return web.json_response({'log': log})

    async def acquire_lock(self, request):
        data = await request.json()
        resource = data.get('resource')
        owner = data.get('owner', self.app['node_id'])
        mode = data.get('mode', 'shared')
        
        if not resource:
            return web.json_response({'error': 'resource required'}, status=400)
        
        success = await self.app['lockman'].acquire(resource, owner, mode)
        return web.json_response({'success': success})

    async def release_lock(self, request):
        data = await request.json()
        resource = data.get('resource')
        owner = data.get('owner', self.app['node_id'])
        
        if not resource:
            return web.json_response({'error': 'resource required'}, status=400)
        
        success = await self.app['lockman'].release(resource, owner)
        return web.json_response({'success': success})

    async def wait_for(self, request):
        edges = self.app['lockman'].local_wait_for_edges()
        return web.json_response({'edges': edges})

    async def produce(self, request):
        data = await request.json()
        topic = data.get('topic')
        message = data.get('message')
        
        if not topic or not message:
            return web.json_response({'error': 'topic and message required'}, status=400)
        
        await self.app['queue'].produce(topic, message)
        return web.json_response({'status': 'ok'})

    async def consume(self, request):
        data = await request.json()
        topic = data.get('topic')
        
        if not topic:
            return web.json_response({'error': 'topic required'}, status=400)
        
        message = await self.app['queue'].consume(topic)
        return web.json_response({'message': message})

    async def cache_get(self, request):
        key = request.query.get('key')
        if not key:
            return web.json_response({'error': 'key required'}, status=400)
        
        value = await self.app['cache'].get(key)
        return web.json_response({'value': value})

    async def cache_put(self, request):
        data = await request.json()
        key = data.get('key')
        value = data.get('value')
        
        if not key or value is None:
            return web.json_response({'error': 'key and value required'}, status=400)
        
        success = await self.app['cache'].put(key, value)
        return web.json_response({'success': success})

    async def cache_invalidate(self, request):
        data = await request.json()
        key = data.get('key')
        
        if not key:
            return web.json_response({'error': 'key required'}, status=400)
        
        await self.app['cache'].handle_invalidate(key)
        return web.json_response({'status': 'ok'})

    async def cache_fetch(self, request):
        key = request.query.get('key')
        if not key:
            return web.json_response({'error': 'key required'}, status=400)
        
        result = await self.app['cache'].handle_fetch(key)
        return web.json_response(result)

    async def cache_state(self, request):
        state = await self.app['cache'].get_cache_state()
        return web.json_response(state)

    async def metrics(self, request):
        """Get metrics in Prometheus format"""
        metrics_data = self.app['metrics'].get_metrics_endpoint_data()
        format_type = request.query.get('format', 'json')
        
        if format_type == 'prometheus':
            return web.Response(
                text=metrics_data['prometheus_format'],
                content_type='text/plain; version=0.0.4; charset=utf-8'
            )
        else:
            return web.json_response(metrics_data['json_format'])
