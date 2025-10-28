import os
import aiohttp
import asyncio
from typing import Optional, Dict, Any

class MessageClient:
    def __init__(self, node_id=None, peers=None):
        self.node_id = node_id
        self.peers = peers or []
        self._session = None
        self._connector = None

    async def _get_session(self):
        """Get or create HTTP session with connection pooling"""
        if self._session is None or self._session.closed:
            self._connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout
            )
        return self._session

    async def close(self):
        """Close HTTP session and connector"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector:
            await self._connector.close()

    def _url(self, target_node, path):
        """Generate URL for target node"""
        # inside docker-compose use service name; outside use localhost:port map
        if os.getenv('DOCKER_ENV'):
            host = target_node
        else:
            host = 'localhost'
        port = 8000 + int(target_node.replace('node',''))
        return f'http://{host}:{port}{path}'

    async def post(self, target_node, path, json_data) -> Optional[Dict[Any, Any]]:
        """Send POST request with improved error handling"""
        url = self._url(target_node, path)
        try:
            session = await self._get_session()
            async with session.post(url, json=json_data) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"POST {url} failed with status {resp.status}")
                    return None
        except asyncio.TimeoutError:
            print(f"POST {url} timed out")
            return None
        except Exception as e:
            print(f"POST {url} failed: {e}")
            return None

    async def get(self, target_node, path) -> Optional[Dict[Any, Any]]:
        """Send GET request with improved error handling"""
        url = self._url(target_node, path)
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"GET {url} failed with status {resp.status}")
                    return None
        except asyncio.TimeoutError:
            print(f"GET {url} timed out")
            return None
        except Exception as e:
            print(f"GET {url} failed: {e}")
            return None
