import os
import glob
import asyncio
import argparse
from itertools import cycle

from bot.utils.proxy_utils_v2 import create_tg_client_proxy_pairs
from pyrogram import Client
from better_proxy import Proxy

from colorama import Fore, Back, Style, init

from bot.config import settings
from bot.utils import logger
from bot.utils.wallets import generate_wallets, get_wallets
from bot.utils.statistics_html import generate_statistics_html_page
from bot.core.tapper import run_tapper
from bot.core.statistics import run_statistics
from bot.core.registrator import register_sessions

init(autoreset=True)

start_text = f"""

🎨️{Fore.CYAN + Style.BRIGHT}Github{Fore.RESET} - https://github.com/YarmolenkoD/paws

My other bots:

💩{Fore.CYAN + Style.BRIGHT}Boinkers{Fore.RESET} - https://github.com/YarmolenkoD/boinkers
🎨{Fore.CYAN + Style.BRIGHT}Notpixel{Fore.RESET} - https://github.com/YarmolenkoD/notpixel

🚀 HIDDEN CODE MARKET 🚀

🐾 PAWS WALLET CONNECTOR - https://t.me/hcmarket_bot?start=referral_355876562-project_1016
🎨 NOTPIXEL PREMIUM - https://t.me/hcmarket_bot?start=referral_355876562-project_1015

Select an action:

    1. {Fore.CYAN + Style.BRIGHT}Run script{Fore.RESET} 🐾
    2. {Fore.CYAN + Style.BRIGHT}Create a session{Fore.RESET} 🐶
    3. {Fore.CYAN + Style.BRIGHT}Statistics{Fore.RESET} 📊

"""

global tg_clients


def get_session_names() -> list[str]:
    session_names = sorted(glob.glob("sessions/*.session"))
    session_names = [
        os.path.splitext(os.path.basename(file))[0] for file in session_names
    ]

    return session_names

async def get_tg_clients() -> list[Client]:
    global tg_clients

    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [
        Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )
        for session_name in session_names
    ]

    return tg_clients


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")

    action = parser.parse_args().action

    if not action:
        print(start_text)

        while True:
            action = input("> ")

            check_array = ["1", "2", "3"]

            if settings.ENABLE_CHECKER:
                check_array = ["1", "2", "3", "4"]

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in check_array:
                logger.warning("Action must be 1, 2 or 3")
            else:
                action = int(action)
                break

    if action == 1:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)

    elif action == 2:
        await register_sessions()

    elif action == 3:
        logger.info('Statistics generation has started... Please wait ⏰')
        tg_clients = await get_tg_clients()
        await statistics(tg_clients=tg_clients)
        logger.success('Statistics successfully generated ✅')
        await generate_statistics_html_page()

    elif action == 4 and settings.ENABLE_CHECKER:
         while True:
             count = input("Input number of wallet you want to create: ")
             try:
                 count = int(count)
                 generate_wallets(count)
                 break
             except Exception as e:
                 logger.error(e)
                 print("Invaild number, please re-enter...")

async def run_tasks(tg_clients: list[Client]):
    client_proxy_list = create_tg_client_proxy_pairs(tg_clients)

    wallets = get_wallets()
    wallets_cycle = cycle(wallets) if wallets else None

    if settings.ENABLE_CHECKER and len(wallets) < len(tg_clients):
        logger.warning(f"<yellow>Wallets not enough for all accounts please generate <red>{len(tg_clients)-len(wallets)}</red> wallets more!</yellow>")
        await asyncio.sleep(3)

    tasks = [
        asyncio.create_task(
            run_tapper(
                tg_client=pair[0],
                proxy=pair[1].as_url,
                wallet=next(wallets_cycle) if wallets_cycle else None,
                wallets=wallets
            )
        )
        for pair in client_proxy_list
    ]

    await asyncio.gather(*tasks)

async def statistics(tg_clients: list[Client]):
    client_proxy_list = create_tg_client_proxy_pairs(tg_clients)

    tasks = [
        asyncio.create_task(
            run_statistics(
                tg_client=pair[0],
                proxy=pair[1].as_url,
            )
        )
        for pair in client_proxy_list
    ]

    await asyncio.gather(*tasks)
