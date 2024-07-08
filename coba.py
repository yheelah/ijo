import asyncio
import ssl
import json
import time
import uuid
import aiohttp
from websockets_proxy import proxy_connect, Proxy
from aiohttp_socks import Socks4ProxyConnector, Socks5ProxyConnector, ProxyConnector
from fake_useragent import UserAgent
from loguru import logger

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_proxy(proxy, proxy_type, user_id, success_proxies):
    try:
        proxy_address = proxy.replace(f'{proxy_type}://', '')
        device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_address))
        logger.info(f"Connecting to {proxy_type.upper()} proxy: {proxy_address} with device ID {device_id}")
        
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
        
        if proxy_type == 'socks5':
            proxy_obj = Proxy.from_url(proxy)
            connector = Socks5ProxyConnector.from_url(proxy)
        elif proxy_type == 'socks4':
            proxy_obj = Proxy.from_url(proxy)
            connector = Socks4ProxyConnector.from_url(proxy)
        elif proxy_type.startswith('http'):
            proxy_obj = Proxy.from_url(proxy)
            connector = ProxyConnector.from_url(proxy)
        else:
            raise ValueError(f"Unknown proxy type: {proxy_type}")
        
        async with proxy_connect(uri, proxy=proxy_obj, ssl=ssl_context, server_hostname=server_hostname,
                                 extra_headers=custom_headers, connector=connector) as websocket:
            
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
            
            success_proxies.append(proxy)
            logger.info(f"Successfully connected to {proxy_type.upper()} proxy: {proxy}")
    
    except Exception as e:
        logger.error(f"Error in {proxy_type.upper()} connection to {proxy}: {str(e)}")

async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('local_proxies.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    success_proxies = []
    tasks = []
    
    for proxy in local_proxies:
        if proxy.startswith('socks5://'):
            proxy_type = 'socks5'
        elif proxy.startswith('socks4://'):
            proxy_type = 'socks4'
        elif proxy.startswith('http://') or proxy.startswith('https://'):
            proxy_type = 'http'
        else:
            logger.warning(f"Unknown proxy type for {proxy}. Skipping.")
            continue
        
        tasks.append(asyncio.create_task(connect_to_proxy(proxy, proxy_type, _user_id, success_proxies)))
    
    await asyncio.gather(*tasks)
    
    # Write all successfully connected proxies to a file
    with open('proxy.txt', 'w') as file:
        for proxy in success_proxies:
            file.write(proxy + '\n')

if __name__ == '__main__':
    asyncio.run(main())
