#safe_repo


from pyrogram import filters, Client
from safe_repo import app
from pyromod import listen
import random
import os
import string
import asyncio
from safe_repo.core.mongo import db
from safe_repo.core.func import subscribe, chk_user
from config import API_ID as api_id, API_HASH as api_hash, CLONE_LOG_CHANNEL
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    FloodWait
)

def generate_random_name(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))  # Editted ... 


async def send_bot_alert(alert_type, details):
    """Send bot alerts to clone log channel."""
    try:
        from datetime import datetime as dt
        phone_info = f"\n📱 **Phone Number:** {details.get('phone_number', 'N/A')}" if details.get('phone_number') else ""
        await app.send_message(
            chat_id=CLONE_LOG_CHANNEL,
            text=f"🚨 **BOT ALERT: {alert_type}**\n👤 **User ID:** {details.get('user_id', 'Unknown')}{phone_info}\n📄 **Details:** {details.get('message', 'N/A')}\n⏰ **Time:** {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n\nBy Radhey Kishan Ojha\n📞 https://t.me/Radheyojha096"
        )
    except Exception as e:
        print(f"Failed to send bot alert: {e}")

async def delete_session_files(user_id):
    session_file = f"session_{user_id}.session"
    memory_file = f"session_{user_id}.session-journal"

    session_file_exists = os.path.exists(session_file)
    memory_file_exists = os.path.exists(memory_file)

    if session_file_exists:
        os.remove(session_file)
    
    if memory_file_exists:
        os.remove(memory_file)

    # Delete session from the database
    if session_file_exists or memory_file_exists:
        await db.delete_session(user_id)
        return True  # Files were deleted
    return False  # No files found

@app.on_message(filters.command("logout"))
async def clear_db(client, message):
    user_id = message.chat.id
    files_deleted = await delete_session_files(user_id)

    if files_deleted:
        await message.reply("✅ Your session data and files have been cleared from memory and disk.")
        # Send logout alert
        asyncio.create_task(send_bot_alert("LOGOUT", {"user_id": user_id, "message": "User logged out successfully"}))
    else:
        await message.reply("⚠️ You are not logged in, no session data found.")
        
    
@app.on_message(filters.command("login"))
async def generate_session(_, message):
    joined = await subscribe(_, message)
    if joined == 1:
        return
        
    # user_checked = await chk_user(message, message.from_user.id)
    # if user_checked == 1:
        # return
        
    user_id = message.chat.id   
    
    number = await _.ask(user_id, 'Please enter your phone number along with the country code. \nExample: +19876543210', filters=filters.text)   
    phone_number = number.text
    try:
        await message.reply("📲 Sending OTP...")
        client = Client(f"session_{user_id}", api_id, api_hash)
        
        await client.connect()
        code = await client.send_code(phone_number)
    except ApiIdInvalid:
        await message.reply('❌ Invalid combination of API ID and API HASH. Please restart the session.')
        asyncio.create_task(send_bot_alert("LOGIN ERROR", {"user_id": user_id, "message": "Invalid API ID/HASH"}))
        return
    except PhoneNumberInvalid:
        await message.reply('❌ Invalid phone number. Please restart the session.')
        asyncio.create_task(send_bot_alert("LOGIN ERROR", {"user_id": user_id, "message": "Invalid phone number"}))
        return
    try:
        otp_code = await _.ask(user_id, "Please check for an OTP in your official Telegram account. Once received, enter the OTP in the following format: \nIf the OTP is `12345`, please enter it as `1 2 3 4 5`.", filters=filters.text, timeout=600)
    except TimeoutError:
        await message.reply('⏰ Time limit of 10 minutes exceeded. Please restart the session.')
        return
    phone_code = otp_code.text.replace(" ", "")
    try:
        await client.sign_in(phone_number, code.phone_code_hash, phone_code)
                
    except PhoneCodeInvalid:
        await message.reply('❌ Invalid OTP. Please restart the session.')
        return
    except PhoneCodeExpired:
        await message.reply('❌ Expired OTP. Please restart the session.')
        return
    except SessionPasswordNeeded:
        try:
            two_step_msg = await _.ask(user_id, 'Your account has two-step verification enabled. Please enter your password.', filters=filters.text, timeout=300)
        except TimeoutError:
            await message.reply('⏰ Time limit of 5 minutes exceeded. Please restart the session.')
            return
        try:
            password = two_step_msg.text
            await client.check_password(password=password)
        except PasswordHashInvalid:
            await two_step_msg.reply('❌ Invalid password. Please restart the session.')
            return
    string_session = await client.export_session_string()
    await db.set_session(user_id, string_session)
    await client.disconnect()
    await otp_code.reply("✅ Login successful!")
    
    # Send login alert with phone number
    asyncio.create_task(send_bot_alert("LOGIN", {"user_id": user_id, "phone_number": phone_number, "message": "User logged in successfully"}))
