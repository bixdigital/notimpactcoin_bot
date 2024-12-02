from telegram import Update
from bot import setup_application
from flask import Request

# Reuse a single Application instance
application = setup_application()
application.initialize()

async def webhook(request: Request):
    try:
        body = await request.json()
        update = Update.de_json(body, application.bot)
        await application.process_update(update)
        return '', 200
    except Exception as e:
        print(f"Error processing update: {e}")
        return str(e), 500
