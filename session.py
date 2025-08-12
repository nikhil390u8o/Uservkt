from telethon import TelegramClient
from telethon.sessions import StringSession
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
)

API_ID = 1234567  # Your Telegram API ID
API_HASH = 'your_api_hash_here'

PHONE, CODE, PASSWORD = range(3)

async def start_gen(update, context):
    await update.message.reply_text("Send me your phone number (with country code):")
    return PHONE

async def phone_handler(update, context):
    phone = update.message.text
    context.user_data['phone'] = phone

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        await client.send_code_request(phone)
        context.user_data['client'] = client
        await update.message.reply_text("Code sent! Please enter the code:")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"Error sending code: {e}")
        return ConversationHandler.END

async def code_handler(update, context):
    code = update.message.text
    client = context.user_data['client']
    phone = context.user_data['phone']

    try:
        me = await client.sign_in(phone, code)
        session_str = client.session.save()
        await update.message.reply_text(f"Here is your session string:\n\n`{session_str}`", parse_mode='Markdown')
        await client.disconnect()
        return ConversationHandler.END
    except Exception as e:
        if 'Password' in str(e):
            await update.message.reply_text("Two-step verification enabled. Please enter your password:")
            return PASSWORD
        else:
            await update.message.reply_text(f"Error signing in: {e}")
            return ConversationHandler.END

async def password_handler(update, context):
    password = update.message.text
    client = context.user_data['client']
    phone = context.user_data['phone']

    try:
        me = await client.sign_in(password=password)
        session_str = client.session.save()
        await update.message.reply_text(f"Here is your session string:\n\n`{session_str}`", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    finally:
        await client.disconnect()
        return ConversationHandler.END

from telegram.ext import Application

def main():
    application = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('gen', start_gen)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_handler)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, code_handler)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
