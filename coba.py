import aiohttp
import asyncio
import random
import ssl
import json
import time
import uuid
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

from loguru import logger

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(socks5_proxy, user_id, success_proxies):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Connecting to {socks5_proxy} with device ID {device_id}")
    
    try:
        await asyncio.sleep(random.randint(1, 10) / 10)
        custom_headers = {
            "User-Agent": random_user_agent,
            "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg"
        }
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        uri = "wss://proxy.wynd.network:4650"
        server_hostname = "proxy.wynd.network"
        proxy = Proxy.from_url(socks5_proxy)
        
        async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                 extra_headers=custom_headers) as websocket:
            
            async def send_ping():
                while True:
                    send_message = json.dumps(
                        {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                    logger.debug(send_message)
                    await websocket.send(send_message)
                    await asyncio.sleep(5)
            
            asyncio.create_task(send_ping())
            
            while True:
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
            
            # If reached here, connection is successful
            success_proxies.append(socks5_proxy)
            logger.info(f"Successfully connected to {socks5_proxy}")
    
    except Exception as e:
        logger.error(f"Error in connection to {socks5_proxy}: {str(e)}")
        logger.error(socks5_proxy)
        
async def connect_to_socks4(proxy, user_id, success_proxies):
    try:
        # Parse proxy address and port from proxy string
        proxy_address = proxy.replace('socks4://', '').replace('socks5://', '')
        
        # Example implementation (using aiohttp for SOCKS4 support)
        connector = aiohttp_socks.SocksConnector.from_url(f'socks4://{proxy_address}')
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.ws_connect('wss://your.websocket.url') as ws:
                await ws.send_str('Hello, websocket!')
                async for msg in ws:
                    print(msg.data)
        
        success_proxies.append(proxy)
        logger.info(f"Successfully connected to SOCKS4 proxy: {proxy}")
    
    except Exception as e:
        logger.error(f"Error in SOCKS4 connection to {proxy}: {str(e)}")
async def connect_to_http(proxy, user_id, success_proxies):
    try:
        # Example implementation (using aiohttp for HTTP/HTTPS proxy)
        connector = aiohttp.ProxyConnector.from_url(proxy)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.ws_connect('wss://your.websocket.url') as ws:
                await ws.send_str('Hello, websocket!')
                async for msg in ws:
                    print(msg.data)
        
        success_proxies.append(proxy)
        logger.info(f"Successfully connected to HTTP/HTTPS proxy: {proxy}")
    
    except Exception as e:
        logger.error(f"Error in HTTP/HTTPS connection to {proxy}: {str(e)}")
        pass  # Do not add failed proxies to success_proxies list

async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('proxy.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    success_proxies = []
    tasks = []
    
    for proxy in local_proxies:
        if proxy.startswith('socks5://'):
            tasks.append(asyncio.ensure_future(connect_to_wss(proxy, _user_id, success_proxies)))
        elif proxy.startswith('socks4://'):
            tasks.append(asyncio.ensure_future(connect_to_socks4(proxy, _user_id, success_proxies)))
        elif proxy.startswith('http://') or proxy.startswith('https://'):
            tasks.append(asyncio.ensure_future(connect_to_http(proxy, _user_id, success_proxies)))
        else:
            logger.warning(f"Unknown proxy type for {proxy}. Skipping.")
    
    await asyncio.gather(*tasks)
    
    # Write only successfully connected proxies back to proxy.txt
    with open('proxy.txt', 'w') as file:
        for proxy in success_proxies:
            file.write(proxy + '\n')


if __name__ == '__main__':
    asyncio.run(main())
