import asyncio
import json
import ssl
import time
import uuid
import random
from websockets import connect as websocket_connect
from fake_useragent import UserAgent
import aiosocksy
from aiohttp import ClientSession
from aiohttp_socks import ProxyConnector
from loguru import logger

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(proxy_url, user_id, success_proxies):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_url))
    logger.info(f"Connecting to {proxy_url} with device ID {device_id}")

    try:
        await asyncio.sleep(random.randint(1, 10) / 10)
        custom_headers = {
            "User-Agent": UserAgent().random,
            "Origin": "chrome-extension://ilehaonighjijnmpnagapkhpcdbhclfg"
        }
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        uri = "wss://proxy.wynd.network:4650"
        server_hostname = "proxy.wynd.network"

        if proxy_url.startswith('socks5://'):
            proxy = Proxy.from_url(proxy_url)
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                await handle_websocket(websocket, device_id, user_id, custom_headers, success_proxies)

        elif proxy_url.startswith('socks4://'):
            proxy_host = proxy_url.split('://')[1]
            proxy_parts = proxy_host.split(':')
            if len(proxy_parts) != 2:
                raise ValueError(f"Invalid SOCKS4 proxy format: {proxy_url}")

            conn = aiosocksy.open_connection(proxy_host=proxy_parts[0], proxy_port=int(proxy_parts[1]),
                                             remote_host=server_hostname, remote_port=4650,
                                             proxy_auth=None, proxy_type=aiosocksy.ProxyType.SOCKS4)

            async with conn as websocket:
                await handle_websocket(websocket, device_id, user_id, custom_headers, success_proxies)

        elif proxy_url.startswith('http://'):
            proxy_host = proxy_url.split('://')[1]
            proxy_parts = proxy_host.split(':')
            if len(proxy_parts) != 2:
                raise ValueError(f"Invalid HTTP proxy format: {proxy_url}")

            proxy = f"http://{proxy_parts[0]}:{proxy_parts[1]}"
            connector = ProxyConnector.from_url(proxy)

            async with ClientSession(connector=connector) as session:
                async with session.ws_connect(uri, ssl=ssl_context, headers=custom_headers) as websocket:
                    await handle_websocket(websocket, device_id, user_id, custom_headers, success_proxies)

        else:
            logger.warning(f"Ignoring unsupported proxy type for {proxy_url}")
            return

        # If we reach here, connection is successful
        success_proxies.append(proxy_url)
        logger.info(f"Successfully connected to {proxy_url}")

    except Exception as e:
        logger.error(f"Error in connection to {proxy_url}: {str(e)}")
        logger.error(proxy_url)
        pass  # Do not add failed proxies to success_proxies list


async def handle_websocket(websocket, device_id, user_id, custom_headers, success_proxies):
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


async def main():
    _user_id = input('Please Enter your user ID: ')
    with open('proxy.txt', 'r') as file:
        local_proxies = file.read().splitlines()

    success_proxies = []
    tasks = [asyncio.ensure_future(connect_to_wss(proxy, _user_id, success_proxies)) for proxy in local_proxies]
    await asyncio.gather(*tasks)

    # Write all proxies (connected and not connected) back to proxy.txt
    with open('proxy.txt', 'w') as file:
        for proxy in local_proxies:
            file.write(proxy + '\n')

if __name__ == '__main__':
    asyncio.run(main())
