import asyncio
import ssl
import json
import time
import uuid
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent
import aiohttp

user_agent = UserAgent()
random_user_agent = user_agent.random

async def check_proxy(proxy_url):
    try:
        async with aiohttp.ClientSession() as session:
            start_time = time.time()
            async with session.get("https://example.com", proxy=proxy_url, timeout=10) as response:
                if response.status == 200:
                    elapsed_time = time.time() - start_time
                    return elapsed_time * 1000  # Convert to milliseconds
                else:
                    return None  # Indicate proxy is not working properly
    except Exception as e:
        logger.error(f"Error checking proxy {proxy_url}: {str(e)}")
        return None  # Indicate proxy is not working properly

async def connect_to_wss(socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Connecting to {socks5_proxy} with device ID {device_id}")
    
    # Check proxy validity
    ping = await check_proxy(socks5_proxy)
    if ping is None:
        logger.info(f"Skipping {socks5_proxy} due to inability to connect or high ping")
        return
    
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
        
        except Exception as e:
            logger.error(f"Error in connection to {socks5_proxy}: {str(e)}")
            logger.error(socks5_proxy)
            continue

async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('proxy.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    # Filter proxies based on connectivity and ping
    valid_proxies = []
    for proxy in local_proxies:
        ping = await check_proxy(proxy)
        if ping is not None:
            valid_proxies.append(proxy)
        else:
            logger.info(f"Proxy {proxy} is not valid and will be skipped.")
    
    tasks = [asyncio.ensure_future(connect_to_wss(proxy, _user_id)) for proxy in valid_proxies]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
