#safe_repo

# ------------------------------------------------------------ #

START_TXT = """
Hi, welcome to Advance Content Saver Bot, designed to save restricted messages from public/private channels and private groups. First login in bot by /login then send post link.
"""

# Motivational quotes related to study (Hindi and English)
MOTIVATIONAL_QUOTES = [
    # English
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
    "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "Believe you can and you're halfway there. - Theodore Roosevelt",
    "Education is the passport to the future, for tomorrow belongs to those who prepare for it today. - Malcolm X",
    "The secret of getting ahead is getting started. - Mark Twain",
    "Every strike brings me closer to the next home run. - Babe Ruth",
    "Hardships often prepare ordinary people for an extraordinary destiny. - C.S. Lewis",
    "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
    
    # Hindi
    "जीवन में सफलता का कोई ईश्वर नहीं होता, केवल एक कोशिश करने वाला होता है।",
    "अपने लक्ष्य की ओर बढ़ते रहो, चाहे रास्ता कितना ही कठिन क्यों न हो।",
    "सफलता का मार्ग कभी भी सीधा नहीं होता, इसे प्राप्त करने के लिए मेहनत करनी पड़ती है।",
    "हर सुबह एक नया अवसर होता है, एक नई कोशिश करने का।",
    "ज्ञान का समुद्र कभी नहीं खत्म होता, जितना आप जानते हैं, उतना ही कम होता है।",
    "किसी भी काम को पूरा करने के लिए दृढ़ता और लगन होनी चाहिए।",
    "सफलता नहीं, प्रयास ही सबसे बड़ी जीत है।",
    "आपका विद्यार्थी जीवन आपके भविष्य का निर्माण करता है, इसे सजा कर रखें।",
    "हर दिन थोड़ी सी प्रगति, एक दिन बहुत बड़ा परिवर्तन ला देगी।",
    "विद्या देने वाले को देवता की तरह पूजा जाता है, क्योंकि वो भविष्य को सजाते हैं।"
]

FORCE_MSG = """
Hey {},

According to my database, you've not joined the updates channel yet. If you want to use me, then join the updates channel and start me again!
"""

HELP_TXT = """
HELP SECTION 📝

🛠️ /settings - Open settings to set your requirements.

🔒 /login - Login to your userbot session.

📦 /batch - Download bulk links in a systematic way.

⛔ /cancel - Stop batch processing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 HOW TO COPY MEDIA FROM BOT:

1️⃣ Login First:
• Use /login command
• Send your session string
• Wait for confirmation

2️⃣ Send Media Links:
• Public channels: https://t.me/channel_name/message_id
• Private channels: https://t.me/c/channel_id/message_id
• Bot messages: https://t.me/b/bot_username/message_id

3️⃣ Batch Download:
• Use /batch command
• Send start link: https://t.me/c/123456/100
• Send end link: https://t.me/c/123456/105
• Bot will download messages 100-105

4️⃣ Customize Output:
• Use /settings to set caption, thumbnail, etc.
• Set custom rename tags
• Configure destination chat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ SUPPORTED MEDIA TYPES:
• 📹 Videos (MP4, MKV, etc.)
• 📸 Photos/Images
• 📄 Documents (PDF, ZIP, etc.)
• 🎵 Audio files
• 📝 Text messages

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 NEED HELP? Contact @Radheyojha096
"""

HELP2_TXT = """
🕵️ Help:

FOR PUBLIC AND PRIVATE CHANNEL OR GROUP:
- First, log in.
- Then send the message link of any channel that you've joined in your login account.

FOR BOT:
- Send the link in this format: https://t.me/b/bot_username/message_id (use Plus Messenger for message_id)

FOR GROUP TOPIC:
- (For Private Group) Group topic link is like: https://t.me/c/xxxxxxxxx/first_id/second_id
But, send it like this: https://t.me/c/xxxxxxx/second_id (remove first id and one /)
- (For Public Group) Follow the private link step but remove "/c" from the link. Ex - https://t.me/username/second_id

#FAQ:

- If the bot says "Have you joined the channel?" then just log in again to the bot and try.

- If your batch is stuck, then use /stop.
"""

ADMIN_TXT = """
ADMINS PANEL 🛠️

➕ /add - Add user ID to the premium section.

➖ /rem - Remove user ID from the premium section.

🔍 /check - Check if a user ID is in the premium section.

📢 /broadcast - Broadcast a message without a forward tag.

📣 /announce - Broadcast a message with a forward tag.

📊 /stats - Check your bot's stats.
"""

SETTINGS_TXT = """
Welcome to the settings section. Here, you can choose button: caption or session and thumbnail.
"""

CAPTI0NS_TXT = """
Customize the bot's caption here to tailor it to your preferences and needs!
"""

THUMBNAIL_TXT = """
Customize the bot's thumbnail here to tailor it to your preferences and needs!
"""

SESSION_TXT = """
Customize the bot's session here to tailor it to your preferences and needs!
"""

CHANNEL_TXT = """
Customize the bot's channel here to tailor it to your preferences and needs!
"""

# ------------------------------------------------------------ #

# Command Help Menu for CMD

CMD_HELP_TXT = """
╔══════════════════════════════════════════════════════════════╗
║              🔧 BOT COMMAND HELP MENU 🔧                     ║
╚══════════════════════════════════════════════════════════════╝

📌 GENERAL COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 🔹 /start - Start the bot & show welcome message
 🔹 /help  - Show help menu with usage instructions
 🔹 /settings - Open settings panel

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 CONTENT COPY/DOWNLOAD COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 🔹 [Single Link] - Copy any media from Telegram
    Usage: Simply paste any Telegram message link
    Example: https://t.me/channel_name/12345
    Example: https://t.me/c/123456789/12345

 🔹 /batch - Download multiple messages in bulk
    Usage: /batch then provide start and end links
    Example: Start: https://t.me/c/123456/100
             End: https://t.me/c/123456/105
    Result: Downloads messages 100-105

 🔹 /cancel - Stop current batch processing
    Usage: /cancel

 🔹 /howtocopy - Detailed guide for copying media
    Usage: /howtocopy (shows step-by-step instructions) (works only during batch process)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 SESSION COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 🔹 /login - Login with your userbot session
    Usage: /login then send session string
    
 🔹 /logout - Logout and delete session
    Usage: /logout

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ CUSTOMIZATION COMMANDS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 🔹 Set Chat ID - Send messages to specific chat
 🔹 Set Rename Tag - Customize file rename tag
 🔹 Caption - Set custom caption for files
 🔹 Replace Words - Replace words in caption
 🔹 Remove Words - Remove specific words from caption
 🔹 Set Thumbnail - Set custom thumbnail image
 🔹 Remove Thumbnail - Delete current thumbnail
 🔹 Reset - Reset all settings to default

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👑 ADMIN COMMANDS (Owner Only):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 🔹 /add <user_id> <time> - Add premium user
    Example: /add 123456789 30d
    
 🔹 /rem <user_id> - Remove premium user
    Example: /rem 123456789
    
 🔹 /check <user_id> - Check premium status
    Example: /check 123456789
    
 🔹 /broadcast <text> - Broadcast message
 🔹 /announce <text> - Broadcast with forward tag
 🔹 /stats - View bot statistics
 🔹 /plan - Manage subscription plans

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 FILE EDIT HISTORY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╔═══════════════════════════════════════════════════════════════╗
║ File Path                              │ Status             ║
╠═══════════════════════════════════════════════════════════════╣
║ safe_repo/core/get_func.py             │ ✅ FIXED            ║
║ safe_repo/core/func.py                  │ ✅ WORKING          ║
║ safe_repo/core/script.py                │ ✅ UPDATED          ║
║ safe_repo/modules/main.py              │ ✅ WORKING          ║
║ safe_repo/modules/start.py              │ ✅ WORKING          ║
║ safe_repo/modules/login.py              │ ✅ WORKING          ║
║ safe_repo/modules/plans.py              │ ✅ WORKING          ║
║ safe_repo/modules/stats.py              │ ✅ WORKING          ║
║ safe_repo/modules/gcast.py              │ ✅ WORKING          ║
║ safe_repo/modules/eval.py               │ ✅ WORKING          ║
║ safe_repo/core/mongo/db.py              │ ✅ WORKING          ║
║ safe_repo/core/mongo/users_db.py       │ ✅ WORKING          ║
║ safe_repo/core/mongo/plans_db.py       │ ✅ WORKING          ║
║ config.py                              │ ✅ CONFIGURED        ║
║ app.py                                 │ ✅ WORKING          ║
╚═══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 BOT STATUS: 🟢 ONLINE

🔹 Clone Function: Working ✅
🔹 Private Channel: Working ✅
🔹 Public Channel: Working ✅
🔹 Batch Download: Working ✅
🔹 Session Login: Working ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 💡 Tip: Use /settings to customize your experience!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 COPY MEDIA EXAMPLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 PUBLIC CHANNEL:
• Link: https://t.me/channel_name/12345
• Bot Action: Downloads and uploads the media

🎯 PRIVATE CHANNEL:
• Link: https://t.me/c/123456789/12345
• Bot Action: Accesses via your session and copies

🎯 BOT MESSAGES:
• Link: https://t.me/b/bot_username/12345
• Bot Action: Copies bot messages and media

🎯 GROUP TOPICS:
• Private: https://t.me/c/123456789/12345
• Public: https://t.me/group_name/12345

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ IMPORTANT NOTES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• 🔐 Login required for private content
• ⏳ Large files may take time to process
• 📊 Premium users get priority processing
• 🚫 Some content may be restricted by Telegram
• 🔄 Bot adds "BY @Radheyojha096" to all uploads

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📞 SUPPORT: @Radheyojha096
__**Powered by safe_repo**__
"""
