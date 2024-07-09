import asyncio
import aiohttp
import ssl
import json
import time
import uuid
from loguru import logger
from fake_useragent import UserAgent

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(proxy_url, proxy_type, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_url))
    logger.info(f"Connecting to {proxy_type} proxy {proxy_url} with device ID {device_id}")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    custom_headers = {
        "User-Agent": random_user_agent,
        "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg"
    }
    
    if proxy_type == 'http':
        connector = aiohttp.TCPConnector(ssl=ssl_context, proxy=f"http://{proxy_url}")
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.ws_connect("wss://proxy.wynd.network:4650", headers=custom_headers) as websocket:
                await handle_websocket(websocket, device_id, user_id, custom_headers)
    
    elif proxy_type == 'socks5':
        from websockets_proxy import Proxy, proxy_connect
        uri = "wss://proxy.wynd.network:4650"
        server_hostname = "proxy.wynd.network"
        proxy = Proxy.from_url(f"socks5://{proxy_url}")
        async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                 extra_headers=custom_headers) as websocket:
            await handle_websocket(websocket, device_id, user_id, custom_headers)
    
    elif proxy_type == 'socks4':
        # Implement SOCKS4 proxy handling here (using aiosocksy or PySocks)
        pass

async def handle_websocket(websocket, device_id, user_id, custom_headers):
    async def send_ping():
        while True:
            send_message = json.dumps(
                {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
            logger.debug(send_message)
            await websocket.send(send_message)
            await asyncio.sleep(5)
    
    asyncio.create_task(send_ping())
    
    while True:
        try:
            response = await websocket.recv()
            
            if not response:
                raise Exception("Empty response received")
            
            message = json.loads(response)
            logger.info(message)
            
            if message.get("action") == "AUTH":
                auth_response = {
                    "id": message["id"],
                    "origin_action": "AUTH",
                    "result": {
                        "browser_id": device_id,
                        "user_id": user_id,
                        "user_agent": custom_headers['User-Agent'],
                        "timestamp": int(time.time()),
                        "device_type": "extension",
                        "version": "4.0.3",
                        "extension_id": "ilehaonighjijnmpnagapkhpcdbhclfg"
                    }
                }
                logger.debug(auth_response)
                await websocket.send(json.dumps(auth_response))
            
            elif message.get("action") == "PONG":
                pong_response = {"id": message["id"], "origin_action": "PONG"}
                logger.debug(pong_response)
                await websocket.send(json.dumps(pong_response))
        
        except Exception as e:
            logger.error(f"Error in websocket connection: {str(e)}")
            break

async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('proxy.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    tasks = []
    for proxy_url in local_proxies:
        if proxy_url.startswith('http'):
            proxy_type = 'http'
        elif proxy_url.startswith('socks5'):
            proxy_type = 'socks5'
        elif proxy_url.startswith('socks4'):
            proxy_type = 'socks4'
        else:
            logger.warning(f"Unsupported proxy type for {proxy_url}. Skipping.")
            continue
        
        tasks.append(asyncio.ensure_future(connect_to_wss(proxy_url, proxy_type, _user_id)))
    
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
