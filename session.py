from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Your bot client (use your bot token here)
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=os.getenv("BOT_TOKEN"))

@bot.on(events.NewMessage(pattern=r"^/genstring$"))
async def gen_string_handler(event):
    sender = await event.get_sender()
    if sender.bot:
        # Ignore other bots or you can restrict to yourself
        return

    chat = await event.get_chat()

    # Start conversation with user for session generation
    async with bot.conversation(chat) as conv:
        await conv.send_message("Send your phone number (with country code, e.g. +123456789):")
        phone = (await conv.get_response()).text.strip()

        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()

        try:
            await client.send_code_request(phone)
        except errors.PhoneNumberInvalidError:
            await conv.send_message("Invalid phone number. Cancelled.")
            await client.disconnect()
            return

        await conv.send_message("Send the login code you received:")
        code = (await conv.get_response()).text.strip()

        try:
            await client.sign_in(phone, code)
        except errors.SessionPasswordNeededError:
            await conv.send_message("Two-step verification enabled. Send your password:")
            password = (await conv.get_response()).text.strip()
            try:
                await client.sign_in(password=password)
            except errors.PasswordHashInvalidError:
                await conv.send_message("Invalid password. Cancelled.")
                await client.disconnect()
                return
        except errors.PhoneCodeInvalidError:
            await conv.send_message("Invalid code. Cancelled.")
            await client.disconnect()
            return

        string_session = client.session.save()
        await conv.send_message(f"✅ Your string session is:\n\n`{string_session}`", parse_mode="markdown")

        await client.disconnect()

if __name__ == "__main__":
    print("Bot is running...")
    bot.run_until_disconnected()
