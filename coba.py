import asyncio
import random
import ssl
import json
import time
import uuid
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
import http.client
import socks

from loguru import logger

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_proxy(proxy_type, proxy_host, proxy_port, user_id, success_proxies):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, f"{proxy_host}:{proxy_port}"))
    logger.info(f"Connecting to {proxy_type} proxy {proxy_host}:{proxy_port} with device ID {device_id}")
    
    try:
        await asyncio.sleep(random.randint(1, 10) / 10)
        custom_headers = {
            "User-Agent": random_user_agent,
            "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg"
        }
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        if proxy_type == 'socks5':
            uri = "wss://proxy.wynd.network:4650"
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(f"socks5://{proxy_host}:{proxy_port}")
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                await handle_connection(websocket, device_id, user_id, custom_headers, success_proxies)
        
        elif proxy_type == 'http':
            conn = http.client.HTTPConnection(proxy_host, proxy_port)
            conn.set_tunnel("proxy.wynd.network", 4650)
            conn.request('CONNECT', "proxy.wynd.network:4650", headers=custom_headers)
            response = conn.getresponse()
            if response.status == 200:
                websocket = conn.sock
                await handle_connection(websocket, device_id, user_id, custom_headers, success_proxies)
            else:
                raise Exception(f"Failed to establish HTTP tunnel ({response.status}): {response.reason}")
        
        elif proxy_type == 'socks4':
            socks.setdefaultproxy(socks.SOCKS4, proxy_host, proxy_port)
            s = socks.socksocket()
            s.connect(("proxy.wynd.network", 4650))
            await handle_connection(s, device_id, user_id, custom_headers, success_proxies)
        
        else:
            raise ValueError(f"Unsupported proxy type: {proxy_type}")
    
    except Exception as e:
        logger.error(f"Error in connection to {proxy_type} proxy {proxy_host}:{proxy_port}: {str(e)}")
        pass  # Do not add failed proxies to success_proxies list

async def handle_connection(websocket, device_id, user_id, custom_headers, success_proxies):
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
    success_proxies.append(f"{proxy_type}://{proxy_host}:{proxy_port}")
    logger.info(f"Successfully connected to {proxy_type} proxy {proxy_host}:{proxy_port}")

async def connect_to_wss(proxy, user_id, success_proxies):
    try:
        proxy_type, proxy_host, proxy_port = parse_proxy_url(proxy)  # Implement a function to parse proxy details
        await connect_to_proxy(proxy_type, proxy_host, proxy_port, user_id, success_proxies)
    
    except Exception as e:
        logger.error(f"Error in parsing proxy {proxy}: {str(e)}")

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
