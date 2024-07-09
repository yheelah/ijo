import asyncio
import json
import logging
import random
import ssl
import time
import uuid

from websockets import connect as ws_connect
from aiohttp_socks import ProxyConnector, ProxyType

logger = logging.getLogger(__name__)

async def connect_to_wss(proxy_url, proxy_type, user_id, success_proxies):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_url))
    logger.info(f"Connecting to {proxy_url} with device ID {device_id}")
    
    try:
        await asyncio.sleep(random.randint(1, 10) / 10)
        custom_headers = {
            "User-Agent": random_user_agent(),
            "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg"
        }
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        uri = "wss://proxy.wynd.network:4650"
        server_hostname = "proxy.wynd.network"
        
        if proxy_type == 'SOCKS5':
            proxy = ProxyConnector.from_url(proxy_url)
        elif proxy_type == 'HTTP':
            proxy = ProxyConnector(proxy_type=ProxyType.HTTP, host=proxy_url.split(':')[1][2:], port=int(proxy_url.split(':')[2]))
        elif proxy_type == 'SOCKS4':
            proxy = ProxyConnector(proxy_type=ProxyType.SOCKS4, host=proxy_url.split(':')[1][2:], port=int(proxy_url.split(':')[2]))
        else:
            raise ValueError(f"Unsupported proxy type: {proxy_type}")

        async with ws_connect(uri, proxy=proxy, ssl=ssl_context, extra_headers=custom_headers) as websocket:
            
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
            success_proxies.append(proxy_url)
            logger.info(f"Successfully connected to {proxy_url}")
    
    except Exception as e:
        logger.error(f"Error in connection to {proxy_url}: {str(e)}")
        logger.error(proxy_url)
        pass  # Do not add failed proxies to success_proxies list

async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('proxy.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    success_proxies = []
    tasks = [asyncio.ensure_future(connect_to_wss(proxy, _user_id, success_proxies)) for proxy in local_proxies]
    await asyncio.gather(*tasks)
    
    # Write only successfully connected proxies back to proxy.txt
    with open('proxy.txt', 'w') as file:
        for proxy in success_proxies:
            file.write(proxy + '\n')

if __name__ == '__main__':
    asyncio.run(main())
