#!/usr/bin/env python3
"""
Sekolah Agama Schedule Reminder Bot
Sends daily schedule reminders to your child via Telegram
"""

import logging
import asyncio
from datetime import datetime, time
import pytz
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import schedule
import threading

# ============================================================
# CONFIGURATION - Edit these values
# ============================================================
BOT_TOKEN = "8580984234:AAEv_YraiQ67dT5RjArz4mlLjViFJGiWlNA"       # From @BotFather
CHAT_ID = "srada_bot"           # Your child's Telegram chat ID
TIMEZONE = "Asia/Kuala_Lumpur"

# Reminder times
NIGHT_BEFORE_TIME = "20:00"   # 8:00 PM - reminder for next day
MORNING_TIME = "04:00"        # 6:00 AM - morning of school
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Malaysia timezone
MY_TZ = pytz.timezone(TIMEZONE)

# ============================================================
# TIMETABLE DATA
# ============================================================
TIMETABLE = {
    "Monday": [
        {"time": "2:30 PM - 3:00 PM", "subject": "Al-Quran 📖"},
        {"time": "3:00 PM - 3:30 PM", "subject": "Al-Quran 📖"},
        {"time": "3:30 PM - 3:50 PM", "subject": "🍱 REHAT (Break)"},
        {"time": "3:50 PM - 4:20 PM", "subject": "Al-Quran 📖"},
        {"time": "4:20 PM - 4:50 PM", "subject": "Bahasa Arab 🌙"},
        {"time": "4:50 PM - 5:20 PM", "subject": "Fiqh 🕌"},
        {"time": "5:20 PM - 5:35 PM", "subject": "Solat Asar Berjemaah 🤲"},
    ],
    "Tuesday": [
        {"time": "2:30 PM - 3:00 PM", "subject": "Al-Quran 📖"},
        {"time": "3:00 PM - 3:30 PM", "subject": "Hafazan 🧠"},
        {"time": "3:30 PM - 3:50 PM", "subject": "🍱 REHAT (Break)"},
        {"time": "3:50 PM - 4:20 PM", "subject": "Jawi ✍️"},
        {"time": "4:20 PM - 4:50 PM", "subject": "Bahasa Arab 🌙"},
        {"time": "4:50 PM - 5:20 PM", "subject": "Jawi ✍️"},
        {"time": "5:20 PM - 5:35 PM", "subject": "Solat Asar Berjemaah 🤲"},
    ],
    "Wednesday": [
        {"time": "2:30 PM - 3:00 PM", "subject": "Al-Quran 📖"},
        {"time": "3:00 PM - 3:30 PM", "subject": "Al-Quran 📖"},
        {"time": "3:30 PM - 3:50 PM", "subject": "🍱 REHAT (Break)"},
        {"time": "3:50 PM - 4:20 PM", "subject": "Jawi ✍️"},
        {"time": "4:20 PM - 4:50 PM", "subject": "Bahasa Arab 🌙"},
        {"time": "4:50 PM - 5:20 PM", "subject": "Jawi ✍️"},
        {"time": "5:20 PM - 5:35 PM", "subject": "Solat Asar Berjemaah 🤲"},
    ],
    "Thursday": [
        {"time": "2:30 PM - 3:00 PM", "subject": "Al-Quran 📖"},
        {"time": "3:00 PM - 3:30 PM", "subject": "Al-Quran 📖"},
        {"time": "3:30 PM - 3:50 PM", "subject": "🍱 REHAT (Break)"},
        {"time": "3:50 PM - 4:20 PM", "subject": "Jawi ✍️"},
        {"time": "4:20 PM - 4:50 PM", "subject": "Tauhid ⭐"},
        {"time": "4:50 PM - 5:20 PM", "subject": "Jawi ✍️"},
        {"time": "5:20 PM - 5:35 PM", "subject": "Solat Asar Berjemaah 🤲"},
    ],
    "Friday": [
        {"time": "2:30 PM - 3:00 PM", "subject": "Al-Quran 📖"},
        {"time": "3:00 PM - 3:30 PM", "subject": "Al-Quran 📖"},
        {"time": "3:30 PM - 3:50 PM", "subject": "🍱 REHAT (Break)"},
        {"time": "3:50 PM - 4:20 PM", "subject": "Jawi ✍️"},
        {"time": "4:20 PM - 4:50 PM", "subject": "Al-Quran 📖"},
        {"time": "4:50 PM - 5:20 PM", "subject": "Perhimpunan 🏫"},
        {"time": "5:20 PM - 5:35 PM", "subject": "Solat Asar Berjemaah 🤲"},
    ],
}

SUBJECT_TIPS = {
    "Al-Quran 📖": "Bring your Quran and practice your recitation!",
    "Hafazan 🧠": "Review your memorization before class!",
    "Bahasa Arab 🌙": "Bring your Arabic exercise book!",
    "Fiqh 🕌": "Bring your Fiqh textbook!",
    "Tauhid ⭐": "Bring your Tauhid textbook!",
    "Jawi ✍️": "Bring your Jawi exercise book and pen!",
    "Akhlaq 💛": "Remember to be kind and respectful today!",
    "Perhimpunan 🏫": "Wear your complete uniform for assembly!",
}


def get_day_schedule(day_name: str) -> str:
    """Build a formatted schedule message for a given day."""
    if day_name not in TIMETABLE:
        return None
    subjects = TIMETABLE[day_name]
    lines = []
    for item in subjects:
        lines.append(f"  🕐 {item['time']}\n      {item['subject']}")
    return "\n".join(lines)


def get_unique_subjects(day_name: str) -> list:
    """Get unique non-break subjects for a day."""
    if day_name not in TIMETABLE:
        return []
    seen = set()
    subjects = []
    for item in TIMETABLE[day_name]:
        s = item["subject"]
        if "REHAT" not in s and "Solat Asar" not in s and s not in seen:
            seen.add(s)
            subjects.append(s)
    return subjects


async def send_morning_reminder(bot: Bot, day_name: str):
    """Send morning reminder for today's schedule."""
    schedule_text = get_day_schedule(day_name)
    subjects = get_unique_subjects(day_name)

    tips = []
    for subj in subjects:
        if subj in SUBJECT_TIPS:
            tips.append(f"• {SUBJECT_TIPS[subj]}")

    tips_text = "\n".join(tips) if tips else "• Have a great day at school!"

    message = (
        f"🌅 *Good Morning! School Day Reminder*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 *{day_name}'s Sekolah Agama Schedule*\n\n"
        f"{schedule_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Reminders:*\n{tips_text}\n\n"
        f"🤲 *Bismillah! Have a blessed day!*"
    )
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    logger.info(f"Morning reminder sent for {day_name}")


async def send_night_reminder(bot: Bot, tomorrow_name: str):
    """Send night reminder for tomorrow's schedule."""
    schedule_text = get_day_schedule(tomorrow_name)
    subjects = get_unique_subjects(tomorrow_name)

    tips = []
    for subj in subjects:
        if subj in SUBJECT_TIPS:
            tips.append(f"• {SUBJECT_TIPS[subj]}")

    tips_text = "\n".join(tips) if tips else "• Prepare your school bag tonight!"

    message = (
        f"🌙 *Good Evening! Tomorrow's Reminder*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Tomorrow ({tomorrow_name}) - Sekolah Agama*\n\n"
        f"{schedule_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🎒 *Prepare Tonight:*\n{tips_text}\n\n"
        f"😴 *Sleep early and be ready! Goodnight!* 🌟"
    )
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    logger.info(f"Night reminder sent for tomorrow: {tomorrow_name}")


async def send_school_starting_reminder(bot: Bot, day_name: str):
    """Send reminder 30 minutes before school starts."""
    message = (
        f"⏰ *School starts in 30 minutes!*\n\n"
        f"Sekolah Agama starts at *2:30 PM* today.\n\n"
        f"✅ Have you:\n"
        f"• Packed your school bag?\n"
        f"• Prepared your Quran / textbooks?\n"
        f"• Had your lunch?\n\n"
        f"🤲 *Bismillah! You've got this!*"
    )
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
    logger.info(f"Pre-school reminder sent for {day_name}")


# ============================================================
# TELEGRAM COMMANDS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"🕌 *Sekolah Agama Schedule Bot*\n\n"
        f"Assalamualaikum! I'm your school schedule reminder bot.\n\n"
        f"Your Chat ID is: `{chat_id}`\n\n"
        f"*Commands:*\n"
        f"/today - Today's schedule\n"
        f"/tomorrow - Tomorrow's schedule\n"
        f"/week - Full week schedule\n"
        f"/day [Monday-Friday] - Specific day schedule",
        parse_mode="Markdown"
    )


async def today_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command."""
    now = datetime.now(MY_TZ)
    day_name = now.strftime("%A")

    if day_name in TIMETABLE:
        schedule_text = get_day_schedule(day_name)
        await update.message.reply_text(
            f"📅 *Today's Schedule ({day_name})*\n\n{schedule_text}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"🎉 No Sekolah Agama today ({day_name})! Enjoy your day off! 😊"
        )


async def tomorrow_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tomorrow command."""
    now = datetime.now(MY_TZ)
    tomorrow = now.weekday() + 1
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    tomorrow_name = days[tomorrow % 7]

    if tomorrow_name in TIMETABLE:
        schedule_text = get_day_schedule(tomorrow_name)
        await update.message.reply_text(
            f"📅 *Tomorrow's Schedule ({tomorrow_name})*\n\n{schedule_text}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"🎉 No Sekolah Agama tomorrow ({tomorrow_name})! Weekend! 🥳"
        )


async def week_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /week command."""
    msg = "📚 *Full Week Schedule - Sekolah Agama*\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        msg += f"📅 *{day}*\n{get_day_schedule(day)}\n\n"
    await update.message.reply_text(msg, parse_mode="Markdown")


async def specific_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /day command."""
    if not context.args:
        await update.message.reply_text("Usage: /day Monday (or any weekday)")
        return
    day = context.args[0].capitalize()
    if day in TIMETABLE:
        schedule_text = get_day_schedule(day)
        await update.message.reply_text(
            f"📅 *{day}'s Schedule*\n\n{schedule_text}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"No schedule found for {day}.")


# ============================================================
# SCHEDULED JOBS
# ============================================================

def run_scheduled_reminders(app: Application):
    """Run scheduled reminders in background thread."""
    async def job_morning():
        now = datetime.now(MY_TZ)
        day_name = now.strftime("%A")
        if day_name in TIMETABLE:
            await send_morning_reminder(app.bot, day_name)

    async def job_night():
        now = datetime.now(MY_TZ)
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        tomorrow_name = days[(now.weekday() + 1) % 7]
        if tomorrow_name in TIMETABLE:
            await send_night_reminder(app.bot, tomorrow_name)

    async def job_preclass():
        now = datetime.now(MY_TZ)
        day_name = now.strftime("%A")
        if day_name in TIMETABLE:
            await send_school_starting_reminder(app.bot, day_name)

    def run_async(coro):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(coro)
        loop.close()

    # Schedule the reminders
    schedule.every().day.at(MORNING_TIME).do(lambda: run_async(job_morning()))
    schedule.every().day.at(NIGHT_BEFORE_TIME).do(lambda: run_async(job_night()))
    schedule.every().day.at("14:00").do(lambda: run_async(job_preclass()))  # 2 PM = 30min before school

    while True:
        schedule.run_pending()
        import time as t
        t.sleep(30)


# ============================================================
# MAIN
# ============================================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Register commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today_schedule))
    app.add_handler(CommandHandler("tomorrow", tomorrow_schedule))
    app.add_handler(CommandHandler("week", week_schedule))
    app.add_handler(CommandHandler("day", specific_day))

    # Start scheduler in background
    scheduler_thread = threading.Thread(
        target=run_scheduled_reminders,
        args=(app,),
        daemon=True
    )
    scheduler_thread.start()

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
