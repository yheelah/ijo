import asyncio
import random
import ssl
import json
import time
import uuid
import aiohttp
from loguru import logger
from websockets_proxy import Proxy, proxy_connect
from fake_useragent import UserAgent

# Generate a random user agent
user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_proxy_and_wss(http_proxy, socks5_proxy, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, socks5_proxy))
    logger.info(f"Connecting to {socks5_proxy} with device ID {device_id}")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                headers = {
                    "User-Agent": random_user_agent
                }

                # Example request using the HTTP proxy
                async with session.get("https://jsonplaceholder.typicode.com/posts/1", proxy=http_proxy, headers=headers) as response:
                    html = await response.text()
                    logger.info(f"Received response from HTTP proxy {http_proxy}: {html}")

                # Simulate some delay
                await asyncio.sleep(random.randint(1, 10))

                # WebSocket connection setup
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

                    # Function to send PING messages periodically
                    async def send_ping():
                        while True:
                            send_message = json.dumps(
                                {"id": str(uuid.uuid4()), "version": "1.0.0", "action": "PING", "data": {}})
                            logger.debug(send_message)
                            await websocket.send(send_message)
                            await asyncio.sleep(5)

                    # Start sending PING messages in the background
                    asyncio.create_task(send_ping())

                    # Receive and process messages from WebSocket
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
                await asyncio.sleep(5)  # Retry every 5 seconds on error

async def main():
    _user_id = input('Please Enter your user ID: ')

    with open('proxi.txt', 'r') as file:
        proxi = file.read().splitlines()

    tasks_connected = []
    tasks_retry = []

    # First pass: connect to proxies
    for index in range(0, len(proxi), 2):
        if proxi[index].startswith("http://"):
            http_proxy = proxi[index]
            if index + 1 < len(proxi) and proxi[index + 1].startswith("socks5://"):
                socks5_proxy = proxi[index + 1]
                tasks_connected.append(asyncio.create_task(connect_to_proxy_and_wss(http_proxy, socks5_proxy, _user_id)))
            else:
                logger.warning(f"Missing or invalid SOCKS5 proxy for HTTP proxy {http_proxy}")
        else:
            logger.warning(f"Unsupported proxy type: {proxi[index]}")

    try:
        await asyncio.gather(*tasks_connected)

        # Second pass: retry failed connections
        for index in range(0, len(proxi), 2):
            if proxi[index].startswith("http://"):
                http_proxy = proxi[index]
                if index + 1 < len(proxi) and proxi[index + 1].startswith("socks5://"):
                    socks5_proxy = proxi[index + 1]
                    tasks_retry.append(asyncio.create_task(connect_to_proxy_and_wss(http_proxy, socks5_proxy, _user_id, retry=True)))
                else:
                    logger.warning(f"Missing or invalid SOCKS5 proxy for HTTP proxy {http_proxy}")
            else:
                logger.warning(f"Unsupported proxy type: {proxi[index]}")

        while tasks_retry:
            await asyncio.gather(*tasks_retry)

            # Clear retry tasks that succeeded
            tasks_retry = [task for task in tasks_retry if not task.done()]

            # Delay before retrying failed tasks
            if tasks_retry:
                await asyncio.sleep(5)  # Retry every 5 seconds on error

    except KeyboardInterrupt:
        logger.info("Process interrupted")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

if __name__ == '__main__':
    logger.add("output.log", rotation="500 MB", level="DEBUG")
    asyncio.run(main())

