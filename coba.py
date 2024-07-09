import asyncio
import random
import ssl
import json
import time
import uuid
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
from aiosocksy import Socks4Proxy, Socks5Proxy  # Install aiosocksy for SOCKS4 support
import aiohttp  # Install aiohttp for HTTP support

from loguru import logger

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(proxy_queue, user_id, success_proxies):
    while True:
        try:
            socks_proxy = await proxy_queue.get()
            device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks_proxy))
            logger.info(f"Connecting to {socks_proxy} with device ID {device_id}")
            
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
            
            # Determine proxy type and create proxy object accordingly
            if socks_proxy.startswith("socks5://"):
                proxy = Proxy.from_url(socks_proxy)
            elif socks_proxy.startswith("socks4://"):
                proxy = Socks4Proxy(socks_proxy.replace("socks4://", ""))
            elif socks_proxy.startswith("http://"):
                proxy = aiohttp.ProxyConnector.from_url(socks_proxy)
            else:
                logger.error(f"Unsupported proxy type for {socks_proxy}")
                continue
            
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
                success_proxies.append(socks_proxy)
                logger.info(f"Successfully connected to {socks_proxy}")
        
        except Exception as e:
            logger.error(f"Error in connection to {socks_proxy}: {str(e)}")
            logger.error(socks_proxy)
            await asyncio.sleep(10)  # Wait before retrying
            await proxy_queue.put(socks_proxy)  # Put proxy back into queue for retry

async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('proxy.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    # Create an asyncio.Queue for managing proxies
    proxy_queue = asyncio.Queue()
    for proxy in local_proxies:
        await proxy_queue.put(proxy)
    
    success_proxies = []
    tasks = [asyncio.ensure_future(connect_to_wss(proxy_queue, _user_id, success_proxies)) for _ in range(len(local_proxies))]
    await asyncio.gather(*tasks)
    
    # Write only successfully connected proxies back to proxy.txt
    with open('proxy.txt', 'w') as file:
        for proxy in success_proxies:
            file.write(proxy + '\n')

if __name__ == '__main__':
    asyncio.run(main())
