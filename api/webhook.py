from telegram import Update
from telegram.ext import Application
from bot import TELEGRAM_BOT_TOKEN, setup_handlers

async def webhook(request):
    try:
        body = await request.json()
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        setup_handlers(application)
        await application.initialize()
        await application.process_update(Update.de_json(body, application.bot))
        return '', 200
    except Exception as e:
        print(f"Error processing update: {e}")
        return '', 500