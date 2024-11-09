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
from bot.utils.logger import SelfTGClient
from bot.exceptions import InvalidSession

self_tg_client = SelfTGClient()

class Tapper:
    def __init__(self, tg_client: Client, wallet: str | None, wallet_memo: str | None):
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0
        self.username = None
        self.first_name = None
        self.last_name = None
        self.fullname = None
        self.start_param = None
        self.peer = None
        self.first_run = None
        self.user = None
        self.session_ug_dict = self.load_user_agents() or []
        self.access_token_created_time = time()
        self.token_live_time = random.randint(500, 900)
        self.referrals_count = 0
        self.scraper = None
        self.wallet = wallet
        self.wallet_connected = False
        self.wallet_memo = wallet_memo
        self.scraper_mode = settings.ENABLE_CLOUDS_SCRAPER

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

            self.start_param = ref_id

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

    def is_night_time(self):
        try:
            night_start = int(settings.NIGHT_TIME[0])
            night_end = int(settings.NIGHT_TIME[1])

            # Get the current hour
            current_hour = datetime.now().hour

            if current_hour >= night_start or current_hour < night_end:
                return True

            return False
        except Exception as error:
            self.error(f"Unknown error during checking night time: <light-yellow>{error}</light-yellow>")
            return False

    def time_until_morning(self):
        try:
            morning_time = datetime.now().replace(hour=int(settings.NIGHT_TIME[1]), minute=0, second=0, microsecond=0)

            if datetime.now() >= morning_time:
                morning_time += timedelta(days=1)

            time_remaining = morning_time - datetime.now()

            return time_remaining.total_seconds() / 60
        except Exception as error:
            self.error(f"Unknown error during calculate time until morning: <light-yellow>{error}</light-yellow>")
            return 0

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip')
            ip = (await response.json()).get('origin')
            logger.info(f"Proxy IP: <cyan>{ip}</cyan>")
        except Exception as error:
            logger.error(f"Proxy: <cyan>{proxy}</cyan> | Error: <ly>{error}</ly>")

    def check_timeout_error(self, error):
         try:
             error_message = str(error)
             is_timeout_error = re.search("504, message='Gateway Timeout'", error_message)
             return is_timeout_error
         except Exception as e:
             return False

    def check_error(self, error, message):
        try:
            error_message = str(error)
            is_equal = re.search(message, error_message)
            return is_equal
        except Exception as e:
            return False

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
        manual_tasks = [
            'manual',
            'kyc',
            'email',
            'boost'
        ]

        if not self.wallet_connected or not settings.ENABLE_CHECKER:
            manual_tasks.append('wallet')

        tasks_to_do = [
            'paragraph',
            'blum',
            'telegram',
            'twitter',
            'invite',
            'emojiname',
            'linked',
            'daily',
        ]

        if not self.wallet_connected and settings.ENABLE_CHECKER:
            tasks_to_do.append('wallet')

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

                    filtered_tasks = []
                    for task in tasks:
                        rewards = sum(reward['amount'] for reward in task['rewards'])

                        progress = task['progress']

                        if progress['claimed']:
                            continue

                        if task.get('type') == 'referral' or task.get('code') == 'referral':
                            required_referrals = progress['total']
                            if self.referrals_count < required_referrals:
                                continue

                        task_code = task.get('code', '').lower()
                        if any(task_to_do in task_code for task_to_do in tasks_to_do):
                            filtered_tasks.append(task)

                    return filtered_tasks
                return []
            except Exception as e:
                self.error(f"Unknown error during getting tasks: {e}")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue
        return None

    async def complete_task(self, http_client: aiohttp.ClientSession, task: dict):
        task_id = task.get('_id', None)
        task_title = task.get('title', 'Unknown task')
        task_type = task.get('type', 'Unknown type')
        task_rewards = sum(reward['amount'] for reward in task.get('rewards', []))
        task_action = task.get('action', 'Unknown action')
        task_data = task.get('data', '')
        task_code = task.get('code', '')
        available_until = task.get('availableUntil', '')

        if task_type == 'social' and task_action == 'link':
             if 't.me/' in task_data:
                 if not settings.UNSAFE_ENABLE_JOIN_TG_CHANNELS:
                     return False

                 self.info(f"Detected Telegram channel subscription task <cyan>{task_title}</cyan>")
                 success = await self.join_telegram_channel(task_data, task_code)
                 if not success:
                     self.error(f"Failed to subscribe to channel <cyan>{task_title}</cyan>")
                     return False
                 await asyncio.sleep(random.uniform(3, 5))

        if task_code == 'daily' and int(time() * 1000) >= available_until:
            return False

        for retry_count in range(settings.MAX_RETRIES):
            try:
                payload = {'questId': task_id}

                status = None

                if self.scraper_mode and self.scraper:
                    response = self.scraper.post(
                        'https://api.paws.community/v1/quests/completed',
                        json=payload,
                    )

                    response.raise_for_status()

                    tasks_data = response.json()

                    status = response.status_code
                else:
                    response = await http_client.post(
                        'https://api.paws.community/v1/quests/completed',
                        json=payload,
                        ssl=settings.ENABLE_SSL,
                    )

                    response.raise_for_status()

                    tasks_data = await response.json()

                    status = response.status

                if status == 201:
                   self.success(f"Task <cyan>{task_title}</cyan> completed successfully")
                   return await self.claim_task_reward(http_client=http_client, task=task)
                else:
                    try:
                        result = await response.json()
                        error_message = result.get('message', 'Unknown error')
                        self.warning(f"Failed to complete task: {error_message}")
                    except:
                        self.error(f"Invalid response")

                    return False


            except Exception as e:
                self.error(f"Unknown error during completing task <cyan>{task_title}</cyan>: {e}")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue
        return None

    async def claim_task_reward(self, http_client: aiohttp.ClientSession, task: dict):
        task_id = task.get('_id', None)
        task_title = task.get('title', 'Unknown task')
        task_type = task.get('type', 'Unknown type')
        task_rewards = sum(reward['amount'] for reward in task.get('rewards', []))
        task_action = task.get('action', 'Unknown action')
        task_data = task.get('data', '')

        url = 'https://api.paws.community/v1/quests/claim'

        for retry_count in range(settings.MAX_RETRIES):
            try:
                payload = { 'questId': task_id }

                status = None

                if self.scraper_mode and self.scraper:
                    response = self.scraper.post(
                        url,
                        json=payload,
                    )

                    response.raise_for_status()

                    tasks_data = response.json()

                    status = response.status_code
                else:
                    response = await http_client.post(
                        url,
                        json=payload,
                        ssl=settings.ENABLE_SSL,
                    )

                    response.raise_for_status()

                    tasks_data = await response.json()

                    status = response.status

                if status == 201 or status == 200:
                   self.success(f"Successfully claimed 🐾 <light-green>{task_rewards}</light-green> 🐾 for task <cyan>{task_title}</cyan>")
                   return True
                else:
                    try:
                        result = await response.json()
                        error_message = result.get('message', 'Unknown error')
                        self.warning(f"Failed to claim reward for task <cyan>{task_title}</cyan>")
                    except:
                        self.error(f"Invalid response")

                    return False


            except Exception as e:
                if retry_count == settings.MAX_RETRIES - 1:
                    self.error(f"Unknown error during claimed task rewards <cyan>{task_title}</cyan>: {e}")
                await asyncio.sleep(delay=random.randint(5, 10))
                continue

        return False

    async def join_telegram_channel(self, channel_url: str, task_code: str) -> bool:
        if not settings.UNSAFE_ENABLE_JOIN_TG_CHANNELS:
            return False

        was_connected = self.tg_client.is_connected

        try:
            if task_code == 'blum':
                channel_username = 'blumcrypto'
            else:
                channel_username = channel_url.split('/')[-1].strip()

            if not channel_username:
                self.error(f"Invalid channel link: <light-yellow>{channel_url}</light-yellow>")
                return False

            if not was_connected:
                await asyncio.sleep(delay=random.randint(3, 6))
                await self.tg_client.connect()
                await asyncio.sleep(delay=random.randint(4, 8))

            try:
                channel = await self.tg_client.get_chat(channel_username)
                await asyncio.sleep(delay=random.randint(3, 6))
            except Exception as e:
                return False

            try:
                member = await self.tg_client.get_chat_member(channel.id, "me")
                if member and member.status not in ["left", "banned", "restricted"]:
                    self.info(f"Already subscribed to channel <cyan>{channel.title}</cyan>")
                    await asyncio.sleep(delay=random.randint(3, 6))
                    if settings.MUTE_AND_ARCHIVE_TG_CHANNELS:
                        await self._mute_and_archive_channel(channel)
                        await asyncio.sleep(delay=random.randint(3, 6))
                    return True
            except Exception as e:
                if not self.check_error(e, 'USER_NOT_PARTICIPANT'):
                    return False

            await self.tg_client.join_chat(channel_username)
            await asyncio.sleep(delay=random.randint(4, 8))
            self.success(f"Successfully subscribed to channel <cyan>{channel.title}</cyan>")
            if settings.MUTE_AND_ARCHIVE_TG_CHANNELS:
                await self._mute_and_archive_channel(channel)
                await asyncio.sleep(delay=random.randint(3, 6))
            return True

        except Exception as e:
            self.error(f"Unexpected error while processing channel {channel_username}: {str(e)}")
            return False
        finally:
            if not was_connected and self.tg_client.is_connected:
                await asyncio.sleep(delay=random.randint(4, 8))
                await self.tg_client.disconnect()

    async def _mute_and_archive_channel(self, channel) -> None:
        try:
            await self.tg_client.invoke(
                raw.functions.account.UpdateNotifySettings(
                    peer=raw.types.InputNotifyPeer(
                        peer=await self.tg_client.resolve_peer(channel.id)
                    ),
                    settings=raw.types.InputPeerNotifySettings(
                        mute_until=2147483647
                    )
                )
            )
            self.info(f"Notifications muted for channel <cyan>{channel.title}</cyan>")
        except Exception as e:
            self.warning(f"Failed to mute notifications: <light-yellow>{str(e)}</light-yellow>")

        try:
            await self.tg_client.invoke(
                raw.functions.folders.EditPeerFolders(
                    folder_peers=[
                        raw.types.InputFolderPeer(
                            peer=await self.tg_client.resolve_peer(channel.id),
                            folder_id=1
                        )
                    ]
                )
            )
            self.info(f"Channel <cyan>{channel.title}</cyan> added to archive")
        except Exception as e:
            self.warning(f"Failed to add to archive: <light-yellow>{str(e)}</light-yellow>")

    async def run_tasks(self, http_client: aiohttp.ClientSession):
        completed_tasks = 0
        total_rewards = 0

        tasks = await self.get_tasks(http_client=http_client)

        if tasks:
            for task in tasks:
                if not task['progress']['claimed']:
                    task_reward = sum(reward['amount'] for reward in task['rewards'])
                    if await self.complete_task(http_client=http_client, task=task):
                        completed_tasks += 1
                        total_rewards += task_reward
                        await asyncio.sleep(delay=random.uniform(5, 10))

    async def bind_wallet(self, http_client: aiohttp.ClientSession):
        url = 'https://api.paws.community/v1/user/wallet'

        try:
            payload = {
                "wallet": self.wallet
            }

            status = None
            success = False
            if self.scraper_mode and self.scraper:
                res = self.scraper.post(url, json=payload)
                status = res.status_code
                success = res.json().get("success") is True
            else:
                res = await http_client.post(url, json=payload, ssl=settings.ENABLE_SSL)
                status = res.status
                parsed = await res.json()
                success = parsed.get("success") is True

            if status == 201 and success:
                return True
            else:
                print(res.text)
                return False
        except Exception as e:
            self.error(f"Unknown error while trying to connect wallet: {e}")
            return False

    async def handle_wallet(self, http_client: aiohttp.ClientSession):
        try:
            if settings.ENABLE_CHECKER and self.wallet is not None:
                self.info(f"Starting to connect with wallet <cyan>{self.wallet}</cyan>")

                check = await self.bind_wallet(http_client=http_client)

                if check:
                    self.success(f"<green>Successfully bind with wallet: <cyan>{self.wallet}</cyan></green>")
                    with open('used_wallet.json', 'r') as file:
                        wallets = json.load(file)

                    wallets.update({
                        self.wallet: {
                            "memonic": self.wallet_memo,
                            "used_for": self.session_name
                        }
                    })

                    self.wallet_connected = True

                    with open('used_wallet.json', 'w') as file:
                        json.dump(wallets, file, indent=4)
                else:
                    self.warning(f"<yellow>Failed to bind with wallet: {self.wallet}</yellow>")
        except Exception as e:
            self.error(f"Unknown error while trying to connect wallet: {e}")
            return False

    async def setup_scraper(self, http_client: aiohttp.ClientSession, proxy: str | None):
        try:
            proxies = None
            if proxy != None:
                if re.search("http://", proxy):
                    proxies = {"http": proxy}
                elif re.search("https://", proxy):
                    proxies = {"http": proxy.replace('https://', 'http://'), "https": proxy}
                elif re.search("socks5://", proxy):
                    proxies = {"http": proxy.replace('socks5://', 'http://'), "socks5": proxy}

            self.scraper = cloudscraper.create_scraper()

            if proxies:
                self.scraper.proxies.update(proxies)

            self.scraper.headers = http_client.headers.copy()

            return True
        except Exception as e:
            return False

    async def run(self, proxy: str | None) -> None:
        if settings.USE_RANDOM_DELAY_IN_RUN:
            random_delay = random.randint(settings.RANDOM_DELAY_IN_RUN[0], settings.RANDOM_DELAY_IN_RUN[1])
            self.info(f"Bot will start in <ly>{random_delay}s</ly>")
            await asyncio.sleep(random_delay)

        access_token = None
        refresh_token = None
        login_need = True

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn)

        if settings.ENABLE_CLOUDS_SCRAPER == True:
            success = await self.setup_scraper(http_client=http_client, proxy=proxy)
            if success:
                self.scraper_mode = True

        if proxy:
            await self.check_proxy(http_client=http_client, proxy=proxy)

        self.access_token_created_time = 0
        self.token_live_time = random.randint(3000, 3600)
        tries_to_login = 4

        while True:
            try:
                if not await self.check_server_availability(http_client=http_client):
                    self.warning(f"<magenta>Paws</magenta> server is not available. Sleep 30 minutes.. 💤")
                    await asyncio.sleep(delay=60 * 30)

                if time() - self.access_token_created_time >= self.token_live_time:
                    login_need = True

                if login_need:
                    if "Authorization" in http_client.headers:
                        del http_client.headers["Authorization"]

                    self.tg_web_data = await self.get_tg_web_data(proxy=proxy)

                    (token, user) = await self.login(http_client=http_client)

                    self.user = user

                    http_client.headers['Authorization'] = f"Bearer {token}"

                    if self.scraper_mode and self.scraper:
                        self.scraper.headers = http_client.headers.copy()

                    self.access_token_created_time = time()
                    self.token_live_time = random.randint(500, 900)

                    if self.first_run is not True and self.tg_web_data and user and token:
                        self.success("Logged in successfully")
                        self.first_run = True
                        login_need = False
                    else:
                        login_need = True

                await asyncio.sleep(delay=3)

            except Exception as error:
                if self.check_timeout_error(error) or self.check_error(error, "Service Unavailable"):
                    self.warning(f"Warning during login: <magenta>Paws</magenta> server is not response.")
                    if tries_to_login > 0:
                        tries_to_login = tries_to_login - 1
                        self.info(f"Login request not always successful, retrying..")
                        await asyncio.sleep(delay=random.randint(10, 40))
                    else:
                        await asyncio.sleep(delay=5)
                        break
                else:
                    self.error(f"Unknown error during login: <light-yellow>{error}</light-yellow>")
                    await asyncio.sleep(delay=5)
                    break

            try:
                if self.user is not None:
                    wallet = user.get('userData', {}).get("wallet", None)

                    referrals_count = user.get('referralData', {}).get('referralsCount', None)

                    if not wallet:
                        wallet_text = "No wallet"
                    else:
                        self.wallet_connected = True

                    current_balance = await self.get_balance(http_client=http_client)

                    if settings.ENABLE_CHECKER:
                        if not wallet:
                            self.info(f"Wallet not connected.")
                        else:
                            self.info(f"Wallet already connected: <cyan>{self.wallet}</cyan> ")

                    if not wallet:
                        await self.handle_wallet(http_client=http_client)

                    if current_balance is None:
                        self.info(f"Current balance: 🐾 Unknown 🐾")
                    else:
                        self.info(f"Current balance: 🐾<light-green>{current_balance}</light-green> 🐾")

                    if referrals_count is None:
                        self.info(f"Referrals count: 🐾 Unknown 🐾")
                    else:
                        self.info(f"Referrals count: 🐶 <cyan>{referrals_count}</cyan> 🐶")

                    if settings.ENABLE_AUTO_TASKS == True:
                        await self.run_tasks(http_client=http_client)
                        await asyncio.sleep(delay=random.randint(2, 5))

                sleep_time = random.randint(int(settings.SLEEP_TIME_IN_MINUTES[0]), int(settings.SLEEP_TIME_IN_MINUTES[1]))
                is_night = False

                if settings.DISABLE_IN_NIGHT:
                    is_night = self.is_night_time()

                if is_night:
                    sleep_time = self.time_until_morning()

                hours = int(sleep_time/60)
                minutes = int(sleep_time % 60)

                if is_night:
                    self.info(f"sleep <cyan>{hours or 0}</cyan> hour(s) and <cyan>{minutes or 0}</cyan> minutes to the morning (to {int(settings.NIGHT_TIME[1])} am hours) 💤")
                else:
                    self.info(f"sleep <cyan>{hours or 0}</cyan> hour(s) and <cyan>{minutes or 0}</cyan> minutes between cycles 💤")

                await asyncio.sleep(delay=sleep_time*60)

            except Exception as error:
                self.error(f"Unknown error: <light-yellow>{error}</light-yellow>")
                await asyncio.sleep(delay=random.randint(5, 10))
            except KeyboardInterrupt:
                 if http_client:
                     try:
                        await http_client.close()
                     except Exception as error:
                         await asyncio.sleep(delay=0.5)
                 await asyncio.sleep(delay=1)

async def run_tapper(tg_client: Client, proxy: str | None, wallet: str | None, wallets: dict | None):
    try:
        wallet_memo = None
        if wallets and wallet:
            wallet_memo = wallets.get(wallet, None)
        await Tapper(tg_client=tg_client, wallet=wallet, wallet_memo=wallet_memo).run(proxy=proxy)
    except InvalidSession:
        self.error(f"{tg_client.name} | Invalid Session")
    except Exception as error:
        await asyncio.sleep(delay=0.5)
