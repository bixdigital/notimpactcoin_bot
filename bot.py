import os
import logging
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from database import Database

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database(MONGODB_URI)


def main_menu():
    """Returns the main menu keyboard layout."""
    return ReplyKeyboardMarkup(
        [
            ["🌾 Farm NotIMPC", "🎰 Spin Now"],
            ["💰 Check Rewards", "📊 Dashboard"],
            ["🔗 Referral Link", "📜 View Tasks"],
        ],
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    args = context.args

    # Handle referral if present
    if args:
        try:
            referrer_id = int(args[0])
            db.add_referral(referrer_id, user_id)
        except ValueError:
            pass

    # Add or update user in the database
    db.add_user(user_id, username)
    db.assign_tasks(user_id)

    await update.message.reply_text(
        "👋 Welcome to the NotImpactCoin bot! 🎮\n\n"
        "Earn NotIMPC rewards by spinning, farming, and completing tasks.\n\n"
        "Use the menu below to navigate:",
        reply_markup=main_menu(),
    )


async def check_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Check Rewards' command."""
    user_id = update.message.from_user.id
    user = db.get_user(user_id)
    await update.message.reply_text(
        f"💰 Your current rewards: {user['rewards']} NOTIMPC.",
        reply_markup=main_menu(),
    )


async def spin_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Spin Now' command."""
    user_id = update.message.from_user.id
    spin_result = random.choice(["Win", "Lose"])
    if spin_result == "Win":
        reward = random.randint(5, 20)
        db.update_rewards(user_id, reward)
        message = f"🎉 You won {reward} NOTIMPC!"
    else:
        message = "😞 Better luck next time!"
    await update.message.reply_text(message, reply_markup=main_menu())


async def farm_notimpc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Farm NotIMPC' command."""
    user_id = update.message.from_user.id
    last_farm_time = db.get_last_farm_time(user_id)
    now = datetime.utcnow()

    if last_farm_time and now - last_farm_time < timedelta(hours=1):
        remaining_time = timedelta(hours=1) - (now - last_farm_time)
        await update.message.reply_text(
            f"⏳ You can farm again in {remaining_time.seconds // 60} minutes.",
            reply_markup=main_menu(),
        )
    else:
        db.update_rewards(user_id, 10)
        db.update_last_farm_time(user_id, now)
        await update.message.reply_text(
            "🌾 You farmed 10 NOTIMPC! Come back in an hour.",
            reply_markup=main_menu(),
        )


async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Referral Link' command."""
    user_id = update.message.from_user.id
    referral_link = f"https://t.me/NotImpactCoinBot?start={user_id}"
    await update.message.reply_text(
        f"🔗 Share your referral link to earn rewards:\n{referral_link}",
        reply_markup=main_menu(),
    )


async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'View Tasks' command."""
    user_id = update.message.from_user.id
    tasks = db.get_tasks(user_id)
    task_list = "\n".join([f"- {task}" for task in tasks])
    await update.message.reply_text(
        f"📜 Your tasks:\n{task_list if task_list else 'No tasks available.'}",
        reply_markup=main_menu(),
    )


def setup_application():
    """Sets up the bot application."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^💰 Check Rewards$"), check_rewards))
    application.add_handler(MessageHandler(filters.Regex("^🎰 Spin Now$"), spin_now))
    application.add_handler(MessageHandler(filters.Regex("^🌾 Farm NotIMPC$"), farm_notimpc))
    application.add_handler(MessageHandler(filters.Regex("^🔗 Referral Link$"), referral_link))
    application.add_handler(MessageHandler(filters.Regex("^📜 View Tasks$"), view_tasks))

    return application
