import os
import logging
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from database import Database

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = Database(MONGODB_URI)

def main_menu():
    return ReplyKeyboardMarkup([
        ["🌾 Farm NotIMPC", "🎰 Spin Now"],
        ["💰 Check Rewards", "📊 Dashboard"],
        ["🔗 Referral Link", "📜 View Tasks"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    args = context.args

    if args:
        try:
            referrer_id = int(args[0])
            db.add_referral(referrer_id, user_id)
        except ValueError:
            pass

    db.add_user(user_id, username)
    db.assign_tasks(user_id)

    await update.message.reply_text(
        "👋 Welcome to the Notimpactcoin bot! 🎮\n\n"
        "Earn NotIMPC rewards by spinning, farming, and completing tasks.\n\n"
        "Use the menu below to navigate:",
        reply_markup=main_menu()
    )

async def check_rewards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = db.get_user(user_id)
    await update.message.reply_text(
        f"💰 Your current rewards: {user['rewards']} NOTIMPC.",
        reply_markup=main_menu()
    )

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = db.get_user(user_id)
    referral_count = db.get_referral_count(user_id)
    
    last_spins = user.get("last_spins", [])
    current_spins = [s for s in last_spins if datetime.strptime(s, "%Y-%m-%d %H:%M:%S") > datetime.now() - timedelta(hours=1)]
    spins_remaining = max(0, 2 - len(current_spins))

    active_benefits = (
        "✨ Stay active to earn more rewards!\n"
        "🌾 Farm rewards regularly, complete spins, and refer friends to earn more NotIMPC!\n"
    )

    await update.message.reply_text(
        f"📊 Dashboard:\n\n"
        f"💰 Rewards: {user['rewards']} NOTIMPC\n"
        f"🔄 Spins used this hour: {len(current_spins)}\n"
        f"🔓 Spins remaining: {spins_remaining}\n"
        f"👥 Referrals: {referral_count}\n\n"
        f"{active_benefits}",
        reply_markup=main_menu()
    )

async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 Share your referral link to earn rewards:\n{link}\n\n"
        f"🎁 Earn additional rewards for every referral!",
        reply_markup=main_menu()
    )

async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    tasks = db.get_tasks(user_id)
    
    task_text = "📜 Your Tasks:\n\n"
    for task in tasks:
        status = "✅" if task["is_completed"] else "⏳"
        task_text += f"{status} {task['task_name']} - {task['task_description']}\n"
        task_text += f"   Reward: {task['reward']} NOTIMPC\n\n"
    
    await update.message.reply_text(task_text, reply_markup=main_menu())

async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = db.get_user(user_id)
    now = datetime.now()

    if user["last_farm_time"]:
        last_farm = datetime.strptime(user["last_farm_time"], "%Y-%m-%d %H:%M:%S")
        if now - last_farm < timedelta(hours=3):
            time_remaining = timedelta(hours=3) - (now - last_farm)
            await update.message.reply_text(
                f"⏳ You can farm again in {time_remaining}.",
                reply_markup=main_menu()
            )
            return

    reward = random.randint(100, 400)
    db.update_user(
        user_id,
        rewards=user["rewards"] + reward,
        last_farm_time=now.strftime("%Y-%m-%d %H:%M:%S")
    )

    await update.message.reply_text(
        f"🌾 You've farmed {reward} NOTIMPC! Your total rewards: {user['rewards'] + reward}.",
        reply_markup=main_menu()
    )

async def spin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = db.get_user(user_id)
    now = datetime.now()

    last_spins = user.get("last_spins", [])
    current_spins = [s for s in last_spins if datetime.strptime(s, "%Y-%m-%d %H:%M:%S") > now - timedelta(hours=1)]

    if len(current_spins) >= 2:
        next_spin = datetime.strptime(current_spins[0], "%Y-%m-%d %H:%M:%S") + timedelta(hours=1)
        time_until_next = next_spin - now
        await update.message.reply_text(
            f"⏳ You can spin again in {time_until_next}.",
            reply_markup=main_menu()
        )
        return

    reward = random.randint(10, 100)
    current_spins.append(now.strftime("%Y-%m-%d %H:%M:%S"))
    
    db.update_user(
        user_id,
        spins=user.get("spins", 0) + 1,
        rewards=user["rewards"] + reward,
        last_spins=current_spins
    )

    # Check if user completed the spin task
    if user.get("spins", 0) + 1 >= 10:
        db.complete_task(user_id, "Spin 10 Times")

    await update.message.reply_text(
        f"🎰 Spin complete! You earned {reward} NOTIMPC. Total rewards: {user['rewards'] + reward}.",
        reply_markup=main_menu()
    )

def setup_handlers(application: Application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^💰 Check Rewards$"), check_rewards))
    application.add_handler(MessageHandler(filters.Regex("^📊 Dashboard$"), dashboard))
    application.add_handler(MessageHandler(filters.Regex("^🔗 Referral Link$"), referral_link))
    application.add_handler(MessageHandler(filters.Regex("^📜 View Tasks$"), view_tasks))
    application.add_handler(MessageHandler(filters.Regex("^🌾 Farm NotIMPC$"), farm))
    application.add_handler(MessageHandler(filters.Regex("^🎰 Spin Now$"), spin))

def run_polling():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    setup_handlers(application)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    run_polling()