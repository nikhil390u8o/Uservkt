from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

from dotenv import load_dotenv
import os

load_dotenv('gen.env')  # loads variables from gen.env

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
PHONE, CODE, PASSWORD = range(3)

async def start_gen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me your phone number with country code (e.g. +123456789):")
    return PHONE

async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    context.user_data['phone'] = phone
    # Create client with no session (new session)
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    context.user_data['client'] = client

    await client.connect()
    try:
        await client.send_code_request(phone)
        await update.message.reply_text("Code sent! Please enter the code you received:")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"Failed to send code: {e}\nPlease send your phone number again:")
        return PHONE

async def code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    phone = context.user_data['phone']
    client: TelegramClient = context.user_data['client']

    try:
        # Sign in
        me = await client.sign_in(phone, code)
    except SessionPasswordNeededError:
        await update.message.reply_text("Two-step verification enabled. Please enter your password:")
        return PASSWORD
    except Exception as e:
        await update.message.reply_text(f"Failed to sign in: {e}\nPlease send the code again:")
        return CODE

    # If success without 2FA password:
    session_str = client.session.save()
    await update.message.reply_text(f"✅ Logged in successfully!\n\nYour String Session:\n`{session_str}`", parse_mode="Markdown")
    await client.disconnect()
    return ConversationHandler.END

async def password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    client: TelegramClient = context.user_data['client']
    phone = context.user_data['phone']

    try:
        me = await client.sign_in(password=password)
    except Exception as e:
        await update.message.reply_text(f"Incorrect password or error: {e}\nPlease enter the password again:")
        return PASSWORD

    session_str = client.session.save()
    await update.message.reply_text(f"✅ Logged in successfully with 2FA!\n\nYour String Session:\n`{session_str}`", parse_mode="Markdown")
    await client.disconnect()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Session generation cancelled.")
    client = context.user_data.get('client')
    if client and client.is_connected():
        await client.disconnect()
    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gen", start_gen)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, code_received)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
