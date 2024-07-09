import asyncio
import aiohttp
import ssl
import json
import time
import uuid
from loguru import logger
from fake_useragent import UserAgent
from websockets_proxy import Proxy, proxy_connect

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(proxy_url, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_url))
    logger.info(f"Connecting to SOCKS5 proxy {proxy_url} with device ID {device_id}")

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    custom_headers = {
        "User-Agent": random_user_agent,
        "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg"
    }
    
    uri = "wss://proxy.wynd.network:4650"
    server_hostname = "proxy.wynd.network"
    proxy = Proxy.from_url(f"socks5://{proxy_url}")
    
    try:
        async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                 extra_headers=custom_headers) as websocket:
            await handle_websocket(websocket, device_id, user_id, custom_headers)
    
    except Exception as e:
        logger.error(f"Error connecting to WebSocket via SOCKS5 proxy {proxy_url}: {str(e)}")

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
    with open('local_socks5_proxies.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    tasks = []
    for proxy_url in local_proxies:
        tasks.append(asyncio.ensure_future(connect_to_wss(proxy_url, _user_id)))
    
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
