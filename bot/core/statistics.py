from datetime import datetime, timedelta, timezone
from dateutil import parser
from time import time
from urllib.parse import unquote, quote
import re
import os
import math
from copy import deepcopy
from PIL import Image
import io
import ssl
import glob
import cloudscraper

from pyrogram.errors import (
    Unauthorized,
    UserDeactivated,
    AuthKeyUnregistered,
    UserNotParticipant,
    ChannelPrivate,
    UsernameNotOccupied,
    FloodWait,
    ChatAdminRequired,
    UserBannedInChannel,
    RPCError
)
from pyrogram import raw
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw import types

from json import dump as dp, loads as ld
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered, FloodWait
from pyrogram.raw.functions.messages import RequestAppWebView
from pyrogram.raw import types

import asyncio
import random
import string
import brotli
import base64
import secrets
import uuid
import aiohttp
import json

from .agents import generate_random_user_agent
from .headers import headers
from .helper import format_duration

from bot.config import settings
from bot.utils import logger
from bot.exceptions import InvalidSession

class Statistics:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.first_name = None
        self.last_name = None
        self.start_param = None
        self.peer = None
        self.user = None
        self.session_ug_dict = self.load_user_agents() or []
        self.scraper = None
        self.scraper_mode = True

        headers['User-Agent'] = self.check_user_agent()

    async def generate_random_user_agent(self):
        return generate_random_user_agent(device_type='android', browser_type='chrome')

    def info(self, message):
        from bot.utils import info
        info(f"<light-yellow>{self.session_name}</light-yellow> | ℹ️ {message}")

    def debug(self, message):
        from bot.utils import debug
        debug(f"<light-yellow>{self.session_name}</light-yellow> | ⚙️ {message}")

    def warning(self, message):
        from bot.utils import warning
        warning(f"<light-yellow>{self.session_name}</light-yellow> | ⚠️ {message}")

    def error(self, message):
        from bot.utils import error
        error(f"<light-yellow>{self.session_name}</light-yellow> | 😢 {message}")

    def critical(self, message):
        from bot.utils import critical
        critical(f"<light-yellow>{self.session_name}</light-yellow> | 😱 {message}")

    def success(self, message):
        from bot.utils import success
        success(f"<light-yellow>{self.session_name}</light-yellow> | ✅ {message}")

    def save_user_agent(self):
        user_agents_file_name = "user_agents.json"

        if not any(session['session_name'] == self.session_name for session in self.session_ug_dict):
            user_agent_str = generate_random_user_agent()

            self.session_ug_dict.append({
                'session_name': self.session_name,
                'user_agent': user_agent_str})

            with open(user_agents_file_name, 'w') as user_agents:
                json.dump(self.session_ug_dict, user_agents, indent=4)

            self.success(f"User agent saved successfully")

            return user_agent_str

    def load_user_agents(self):
        user_agents_file_name = "user_agents.json"

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("User agents file not found, creating...")

        except json.JSONDecodeError:
            logger.warning("User agents file is empty or corrupted.")

        return []

    def get_wallet_memo(self):
        user_agents_file_name = "user_agents.json"

        try:
            with open(user_agents_file_name, 'r') as user_agents:
                session_data = json.load(user_agents)
                if isinstance(session_data, list):
                    return session_data

        except FileNotFoundError:
            logger.warning("User agents file not found, creating...")

        except json.JSONDecodeError:
            logger.warning("User agents file is empty or corrupted.")

        return []

    def check_user_agent(self):
        load = next(
            (session['user_agent'] for session in self.session_ug_dict if session['session_name'] == self.session_name),
            None)

        if load is None:
            return self.save_user_agent()

        return load

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            if settings.USE_REF == True and settings.REF_ID:
                ref_id = settings.REF_ID
            else:
                ref_id = 'xDZm2M3t'

            self.start_param = random.choices([ref_id, 'xDZm2M3t'], weights=[70, 30])[0]

            peer = await self.tg_client.resolve_peer('PAWSOG_bot')
            InputBotApp = types.InputBotAppShortName(bot_id=peer, short_name="PAWS")

            web_view = await self.tg_client.invoke(RequestAppWebView(
                peer=peer,
                app=InputBotApp,
                platform='android',
                write_allowed=True,
                start_param=self.start_param
            ))

            auth_url = web_view.url

            tg_web_data = unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

            try:
                if self.user_id == 0:
                    information = await self.tg_client.get_me()
                    self.user_id = information.id
                    self.first_name = information.first_name or ''
                    self.last_name = information.last_name or ''
                    self.username = information.username or ''
            except Exception as e:
                print(e)

            if with_tg is False:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            self.error(f"Session error during Authorization: <light-yellow>{error}</light-yellow>")
            await asyncio.sleep(delay=10)

        except Exception as error:
            self.error(
                f"Unknown error during Authorization: <light-yellow>{error}</light-yellow>")
            await asyncio.sleep(delay=random.randint(3, 8))

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = self.scraper.get(url='https://httpbin.org/ip')
            ip = response.json().get('origin')
#             logger.info(f"Proxy IP: <cyan>{ip}</cyan>")
            return True
        except Exception as error:
            logger.warning(f"<ly>Something went wrong with proxy</ly>: <cyan>{proxy}</cyan>")

    async def login(self, http_client: aiohttp.ClientSession):
        url = 'https://api.paws.community/v1/user/auth'

        payload = {
            'data': self.tg_web_data,
            'referralCode': self.start_param
        }

        for retry_count in range(settings.MAX_RETRIES):
            try:
                if self.scraper_mode and self.scraper:
                     response = self.scraper.post(
                         url,
                         json=payload,
                     )

                     response.raise_for_status()

                     login_data = response.json()
                else:
                    response = await http_client.post(
                        url,
                        json=payload,
                        ssl=settings.ENABLE_SSL,
                    )

                    response.raise_for_status()

                    login_data = await response.json()

                if not login_data.get('data'):
                    self.error(f"Error during login | Invalid server response: {login_data}")
                    return (None, None)

                access_token = login_data['data'][0]
                user = login_data['data'][1]

                return (access_token, user)
            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    self.error(f"Unknown error during login: {e}")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue
        return (None, None)

    async def get_user_info(self, http_client: aiohttp.ClientSession):
        url = 'https://api.paws.community/v1/user'
        for retry_count in range(settings.MAX_RETRIES):
            try:
                if self.scraper_mode and self.scraper:
                     response = self.scraper.get(
                         url,
                     )

                     response.raise_for_status()

                     user_data = response.json()
                else:
                    response = await http_client.get(
                        url,
                        ssl=settings.ENABLE_SSL,
                    )

                    response.raise_for_status()

                    user_data = await response.json()

                return user_data
            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    self.error(f"Unknown error during getting user info: <light-yellow>{e}</light-yellow>")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue
        return None

    async def get_balance(self, http_client):
        try:
            user = await self.get_user_info(http_client=http_client)

            balance = user['data'].get('gameData', {}).get('balance', 0)

            return balance
        except Exception as e:
            self.error(f"Unknown error during getting balance: <light-yellow>{e}</light-yellow>")
            await asyncio.sleep(delay=random.randint(5, 10))
            return 0

    async def check_server_availability(self, http_client: aiohttp.ClientSession):
        try:
            status = None
            if self.scraper_mode and self.scraper:
                response = self.scraper.get(
                    'https://api.paws.community/v1/health',
                )
                status = response.status_code
            else:
                response = await http_client.get(
                    'https://api.paws.community/v1/health',
                    ssl=settings.ENABLE_SSL,
                )
                status = response.status

            if status == 200:
                return True

            return False
        except Exception as e:
            return False

    async def get_tasks(self, http_client: aiohttp.ClientSession):
        for retry_count in range(settings.MAX_RETRIES):
            try:
                if self.scraper_mode and self.scraper:
                    response = self.scraper.get(
                        'https://api.paws.community/v1/quests/list',
                    )

                    response.raise_for_status()

                    tasks_data = response.json()
                else:
                    response = await http_client.get(
                        'https://api.paws.community/v1/quests/list',
                        ssl=settings.ENABLE_SSL,
                    )

                    response.raise_for_status()

                    tasks_data = await response.json()

                if tasks_data.get('success') and tasks_data.get('data'):
                    tasks = tasks_data['data']

                    return tasks
                return []
            except Exception as e:
                await asyncio.sleep(delay=random.randint(3, 6))
                continue
        return []

    async def setup_scraper(self, http_client: aiohttp.ClientSession, proxy: str | None):
        try:
            proxies = None
            if proxy != None:
                if re.search("http://", proxy):
                    proxies = {"http": proxy}
                elif re.search("https://", proxy):
                    proxies = {"http": proxy.replace('https://', 'http://'), "https": proxy}
                elif re.search("socks5://", proxy):
                    proxies = {"socks5": proxy}

            self.scraper = cloudscraper.create_scraper()

            if proxies:
                self.scraper.proxies.update(proxies)

            self.scraper.headers = http_client.headers.copy()

            return True
        except Exception as e:
            return False

    async def run(self, proxy: str | None) -> None:
        if settings.RANDOM_DELAY_IN_RUN_STATISTICS:
            random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN_STATISTICS[0], settings.RANDOM_DELAY_IN_RUN_STATISTICS[1])
#             self.info(f"Bot will start in <ly>{random_delay}s</ly>")
            await asyncio.sleep(random_delay)

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        await self.setup_scraper(http_client=http_client, proxy=proxy)

        await asyncio.sleep(delay=2)

        try:
            if not await self.check_server_availability(http_client=http_client):
                self.warning(f"<magenta>Paws</magenta> server is not available. Try later..")
                return None

            self.tg_web_data = await self.get_tg_web_data(proxy=proxy)

            (token, user) = await self.login(http_client=http_client)

            self.user = user

            http_client.headers['Authorization'] = f"Bearer {token}"
            self.scraper.headers = http_client.headers.copy()

            await asyncio.sleep(delay=3)

        except Exception as error:
            return None

        try:
            if self.user is not None:
                file_path = 'statistics.json'

                wallet = self.user.get('userData', {}).get("wallet", 'Unknown')

                referrals_count = self.user.get('referralData', {}).get('referralsCount', 0)
                referrals_code = self.user.get('referralData', {}).get('code', None)

                if referrals_code:
                    referrals_link = f"https://t.me/PAWSOG_bot/PAWS?startapp={referrals_code}"
                else:
                    referrals_link = 'https://t.me/PAWSOG_bot/PAWS'

                balance = await self.get_balance(http_client=http_client)

                if not os.path.exists(file_path):
                    with open(file_path, 'w') as file:
                        json.dump({}, file)

                with open(file_path, 'r') as file:
                    statistics = json.load(file)

                statistics.update({
                    self.session_name: {
                        "name": self.session_name,
                        "userId": self.user_id,
                        "referrals": referrals_count,
                        "referralLink": referrals_link,
                        "wallet": wallet,
                        "balance": balance,
                    }
                })

                with open(file_path, 'w') as file:
                    json.dump(statistics, file, indent=4)

        except Exception as error:
            self.error(f"Unknown error: <light-yellow>{error}</light-yellow>")
            await asyncio.sleep(delay=random.randint(5, 10))
        except KeyboardInterrupt:
             await asyncio.sleep(delay=1)


async def run_statistics(tg_client: Client, proxy: str | None):
    try:
        await Statistics(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        self.error(f"{tg_client.name} | Invalid Session")
    except Exception as error:
        await asyncio.sleep(delay=0.5)
