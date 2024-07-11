import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
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
                
                ping_task = asyncio.create_task(send_ping())
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=15)
                        
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
                    
                    except asyncio.TimeoutError:
                        logger.error(f"Timeout error on {socks5_proxy}. Retrying connection.")
                        break
        
        except Exception as e:
            logger.error(f"Error in connection to {socks5_proxy}: {str(e)}")
            logger.error(socks5_proxy)
            continue

async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('proxi.txt', 'r') as file:
            proxi = file.read().splitlines()
    tasks = [asyncio.ensure_future(connect_to_wss(i, _user_id)) for i in proxi ]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
