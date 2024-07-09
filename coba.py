import asyncio
import ssl
import json
import time
import uuid
from loguru import logger
from aiohttp import ClientSession, ClientTimeout
import aiohttp_socks
from fake_useragent import UserAgent

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Connecting to {socks5_proxy} with device ID {device_id}")
    
    while True:
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
            proxy = aiohttp_socks.Socks5Proxy(socks5_proxy)
            
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                
                async def send_ping():
                    while True:
                        send_message = json.dumps(
                            {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                        logger.debug(send_message)
                        await websocket.send_str(send_message)
                        await asyncio.sleep(5)
                
                asyncio.create_task(send_ping())
                
                while True:
                    response = await websocket.receive()
                    
                    if not response:
                        raise Exception("Empty response received")
                    
                    message = json.loads(response.data)
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
                        await websocket.send_str(json.dumps(auth_response))
                    
                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        logger.debug(pong_response)
                        await websocket.send_str(json.dumps(pong_response))
        
        except Exception as e:
            logger.error(f"Error in connection to {socks5_proxy}: {str(e)}")
            logger.error(socks5_proxy)
            continue

async def connect_to_http_proxy(http_proxy, user_id):
    # Example implementation using aiohttp for HTTP proxies
    async with ClientSession() as session:
        while True:
            try:
                async with session.ws_connect("wss://proxy.wynd.network:4650") as ws:
                    # WebSocket connection logic with HTTP proxy
                    pass
            except Exception as e:
                logger.error(f"Error connecting to HTTP proxy {http_proxy}: {e}")
                await asyncio.sleep(10)

async def connect_to_socks4_proxy(socks4_proxy, user_id):
    # Example implementation using aiosocksy for SOCKS4 proxies
    while True:
        try:
            async with aiohttp_socks.Socks4Session() as session:
                async with session.ws_connect("wss://proxy.wynd.network:4650", proxy=socks4_proxy) as ws:
                    # WebSocket connection logic with SOCKS4 proxy
                    pass
        except Exception as e:
            logger.error(f"Error connecting to SOCKS4 proxy {socks4_proxy}: {e}")
            await asyncio.sleep(10)

async def main():
    _user_id = input('Please Enter your user ID: ')
    
    with open('local_proxies.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    tasks = []
    for proxy in local_proxies:
        if proxy.startswith('http'):
            tasks.append(asyncio.ensure_future(connect_to_http_proxy(proxy, _user_id)))
        elif proxy.startswith('socks4'):
            tasks.append(asyncio.ensure_future(connect_to_socks4_proxy(proxy, _user_id)))
        elif proxy.startswith('socks5'):
            tasks.append(asyncio.ensure_future(connect_to_wss(proxy, _user_id)))
    
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
