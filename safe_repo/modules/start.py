import random
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from safe_repo import app
from safe_repo.core import script
from safe_repo.core.func import subscribe
from safe_repo.core.mongo import db as mdb
from safe_repo.core.mongo.plans_db import check_premium, add_premium
from safe_repo.core.mongo.users_db import add_user, get_user
from config import OWNER_ID, CLONE_LOG_CHANNEL
from datetime import datetime, timedelta, timezone

# ------------------- Start-Buttons ------------------- #

buttons = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Help", callback_data='show_help'), InlineKeyboardButton("Settings", callback_data='show_settings')],
        [InlineKeyboardButton("Join Channel", url="https://t.me/radheyojha9")],
        [InlineKeyboardButton("Buy Premium", url="https://t.me/Radheyojha096")]
    ]
)

@app.on_message(filters.command("start"))
async def start(_, message):
    join = await subscribe(_, message)
    if join == 1:
        return
    
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    
    # Check if user is new and give free trial
    premium_check = await check_premium(user_id)
    if premium_check is None:
        # User doesn't have premium, give 15 days free trial
        expire_date = datetime.now(timezone.utc) + timedelta(days=15)
        await add_premium(user_id, expire_date)
        
        # Add user to users_db if not already
        user_exists = await get_user(user_id)
        if not user_exists:
            await add_user(user_id)
        
        # Send welcome message with trial info
        trial_msg = f"""🎉 **Welcome to Safe Repo Bot!**

👋 Hello {message.from_user.mention}!

You've been granted a **15-day FREE TRIAL** of our premium features! 🚀

⏰ **Trial Expires:** {expire_date.strftime('%Y-%m-%d %H:%M:%S UTC')}

Enjoy full access to all premium features during your trial period.

For any questions, contact support: @Radheyojha096"""
        
        await message.reply_text(trial_msg)
        
        # Send alert to log channel
        try:
            log_msg = f"""🎁 **NEW USER FREE TRIAL**

👤 **User:** {user_name} ({user_id})
📱 **User ID:** `{user_id}`
⏰ **Trial Granted:** 15 days
📅 **Expires:** {expire_date.strftime('%Y-%m-%d %H:%M:%S UTC')}

By Radhey Kishan Ojha
📞 https://t.me/Radheyojha096"""
            await app.send_message(chat_id=CLONE_LOG_CHANNEL, text=log_msg)
        except Exception as e:
            print(f"Failed to send trial alert: {e}")
    
    # Check if user has an active session (logged in)
    data = await mdb.get_data(message.from_user.id)
    session = None
    if data:
        session = data.get("session")
    status_text = "🔓 You are logged in." if session else "🔒 You are logged out."
    
    # Get random motivational quote
    quote = random.choice(script.MOTIVATIONAL_QUOTES)
    
    await message.reply_text(
        text=script.START_TXT.format(message.from_user.mention) + 
             f"\n\n{status_text}\n\n💭 **Daily Motivation:**\n\"{quote}\"",
        reply_markup=buttons
    )

@app.on_callback_query(filters.regex('show_help'))
async def show_help_callback(_, callback_query):
    help_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Usage Instructions", callback_data='show_help2')],
            [InlineKeyboardButton("Back", callback_data='back_to_start')]
        ]
    )
    await callback_query.answer()
    await callback_query.edit_message_text(
        text=script.HELP_TXT,
        reply_markup=help_buttons
    )

@app.on_callback_query(filters.regex('show_help2'))
async def show_help2_callback(_, callback_query):
    help2_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Back to Help", callback_data='show_help')],
            [InlineKeyboardButton("Back to Start", callback_data='back_to_start')]
        ]
    )
    await callback_query.answer()
    await callback_query.edit_message_text(
        text=script.HELP2_TXT,
        reply_markup=help2_buttons
    )

@app.on_callback_query(filters.regex('show_settings'))
async def show_settings_callback(_, callback_query):
    settings_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Back", callback_data='back_to_start')]
        ]
    )
    await callback_query.answer()
    await callback_query.edit_message_text(
        text=script.SETTINGS_TXT,
        reply_markup=settings_buttons
    )

@app.on_message(filters.command("help"))
async def help_command(_, message):
    join = await subscribe(_, message)
    if join == 1:
        return
    
    help_buttons = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Usage Instructions", callback_data='show_help2')],
            [InlineKeyboardButton("Back to Start", callback_data='back_to_start')]
        ]
    )
    await message.reply_text(
        text=script.HELP_TXT,
        reply_markup=help_buttons
    )

@app.on_callback_query(filters.regex('back_to_start'))
async def back_to_start_callback(_, callback_query):
    # Check if user has an active session (logged in)
    data = await mdb.get_data(callback_query.from_user.id)
    session = None
    if data:
        session = data.get("session")
    status_text = "🔓 You are logged in." if session else "🔒 You are logged out."
    
    # Get random motivational quote
    quote = random.choice(script.MOTIVATIONAL_QUOTES)
    
    await callback_query.answer()
    await callback_query.edit_message_text(
        text=script.START_TXT.format(callback_query.from_user.mention) + 
             f"\n\n{status_text}\n\n💭 **Daily Motivation:**\n\"{quote}\"",
        reply_markup=buttons
    )
