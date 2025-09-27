import time
import random
import re
import asyncio
import logging
import json
import os
import aiohttp
from datetime import datetime, timedelta
from telethon import TelegramClient, events, types, functions
from telethon.tl.types import (
    MessageEntityMentionName, MessageEntityTextUrl,
    MessageEntityBold, MessageEntityItalic,
    MessageEntityCode, MessageEntityPre,
    UserStatusOnline, UserStatusOffline,
    UserStatusRecently, UserStatusLastWeek,
    UserStatusLastMonth
)
from telethon.tl.functions.messages import ForwardMessagesRequest, SendMessageRequest
from telethon.tl.functions.contacts import GetContactsRequest, SearchRequest
from telethon.tl.functions.users import GetFullUserRequest

# Enhanced logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_activity.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration - Replace with your actual credentials
api_id = 17349  # Your actual API ID
api_hash = '344583e45741c457fe1862106095a5eb'  # Your actual API hash

# Session file
session_file = 'my_main_account'

# Initialize client
client = TelegramClient(session_file, api_id, api_hash)

# Configuration
ADMIN_USER_ID = 8072333394  # @Call_Me_Ashik (Admin)
FORWARD_USER_ID = 5998427438  # User to forward messages to
SOURCE_BOT_USERNAME = 'MasterOrderRobot'
ADMIN_USER_IDS = [ADMIN_USER_ID, 8072333394]  # Add other admin IDs
BACKUP_INTERVAL = 3600  # Backup every hour (in seconds)
MESSAGE_HISTORY_LIMIT = 1000  # Limit of messages to keep in history
AI_API_URL = "https://api.mastertopupbazar.shop/gpt/ai.php?text="

# Data storage files
CONVERSATION_HISTORY_FILE = 'conversation_history.json'
USER_STATS_FILE = 'user_statistics.json'

# Enhanced conversation database
conversation_context = {}
message_history = []
user_statistics = {}

# Load existing data
def load_data():
    global conversation_context, message_history, user_statistics
    try:
        if os.path.exists(CONVERSATION_HISTORY_FILE):
            with open(CONVERSATION_HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                conversation_context = data.get('conversation_context', {})
                message_history = data.get('message_history', [])

        if os.path.exists(USER_STATS_FILE):
            with open(USER_STATS_FILE, 'r', encoding='utf-8') as f:
                user_statistics = json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")

# Save data to files
def save_data():
    try:
        with open(CONVERSATION_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'conversation_context': conversation_context,
                'message_history': message_history[-MESSAGE_HISTORY_LIMIT:]  # Keep only recent messages
            }, f, ensure_ascii=False, indent=2)

        with open(USER_STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_statistics, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")

# Response templates with more variety and better Bengali support
greetings = ['hello', 'hey', 'hi', 'হ্যালো', 'হাই', 'হেই', 'হেলো', 'assalamualaikum', 'আসসালামু আলাইকুম', 'good morning', 'good evening', 'good afternoon']
how_are_you_responses = [
    'আমি ভালো আছি, ধন্যবাদ! আপনার খবর কি?',
    'এই তো, চলে যাচ্ছে। আপনি কেমন আছেন?',
    'আলহামদুলিল্লাহ্‌, ভালো। আপনাকে কীভাবে সাহায্য করতে পারি?',
    'ভালো আছি, আপনাকে ধন্যবাদ জিজ্ঞাসা করার জন্য!',
    'পুরোপুরি ফিট আছি! আপনার জন্য কি করতে পারি?',
    'সবচেয়ে ভালো নেই, কিন্তু আপনার সাথে কথা বলে ভালো লাগছে!'
]
what_are_you_doing_responses = [
    'এই তো, কিছু কাজ করছিলাম।',
    'তেমন কিছু না, আপনার সাথে কথা বলছি।',
    'আমি একটি অটোমেটেড স্ক্রিপ্ট, তাই সবসময় অনলাইন থাকি।',
    'আপনার মেসেজের জন্য অপেক্ষা করছিলাম!',
    'টেলিগ্রাম মেসেজ মনিটর করছি। আপনার কোনো সহায়তা প্রয়োজন?',
    'সিস্টেম আপডেট করছিলাম, এখন সম্পূর্ণরূপে কাজ করতে প্রস্তুত!'
]
thanks_responses = [
    'আপনাকে স্বাগতম!',
    'কোনো সমস্যা না!',
    'আবার কথা বলবেন!',
    'আমার জন্য আনন্দের বিষয় আপনাকে সাহায্য করতে পারা!',
    'আপনার সন্তুষ্টিই আমার priorit!',
    'আবারও কোনো সাহায্যের প্রয়োজন হলে জানাবেন।'
]
unknown_responses = [
    'দুঃখিত, আমি এখনো সেই প্রশ্নের উত্তর দিতে শিখিনি।',
    'মাফ করবেন, আমি বুঝতে পারিনি। আপনি অন্যভাবে বলতে পারেন?',
    'আমি এখনো সেই বিষয়ে জানি না, অন্য কিছু জিজ্ঞাসা করুন।',
    'আমি একটি বট, আরও জটিল প্রশ্নের উত্তর দিতে পারি না।',
    'আপনার প্রশ্নটি রেকর্ড করা হয়েছে, ভবিষ্যতে আপডেটে উত্তর যোগ করা হবে।'
]

# Bengali-English mixed language processor
def process_benglish_text(text):
    """Process mixed Bengali-English text and convert to appropriate responses"""
    # Common Benglish patterns
    benglish_patterns = {
        r'\b(apni|tumi|tui|you)\s+(kemon|kmon|kman|how)\s+(acho|achho|achoo|aso|are)\b': 'how_are_you',
        r'\b(ki|what)\s+(korcho|korchoo|korchen|korchis|doing)\b': 'what_doing',
        r'\b(dhonnobad|thanks|thank you|thnx|tnx)\b': 'thanks',
        r'\b(hello|hi|hey|hy|halo|hilu)\b': 'greeting',
        r'\b(time|somoy|taiym|samay)\s+(koto|kta|kitay|kitha)\b': 'time_inquiry',
        r'\b(date|tarikh|today|aj)\s+(ki|koto|kitha)\b': 'date_inquiry',
        r'\b(help|sahayjo|sahazz|sahajjo|help me)\b': 'help',
        r'\b(who are you|tumi ke|apni ke|bot er nam|your name)\b': 'who_are_you',
        r'\b(order|order korbo|order dete|order debo)\b': 'order_related',
        r'\b(bye|bbye|goodbye|see you|allah hafiz|byee)\b': 'goodbye'
    }

    text_lower = text.lower()
    for pattern, intent in benglish_patterns.items():
        if re.search(pattern, text_lower):
            return intent
    return None

# User status tracking with more details
user_status = {}
user_activity = {}

# Forward tag removal function with enhanced media handling
async def forward_without_tag(chat_id, message):
    try:
        # Check if message is from the source bot
        sender = await message.get_sender()
        is_from_bot = sender and ((hasattr(sender, 'username') and sender.username and
                                 sender.username.lower() == SOURCE_BOT_USERNAME.lower()))

        # Prepare caption (for media messages)
        caption = message.text or message.message
        entities = []
        # Filter entities to remove forward tags but keep formatting
        if message.entities:
            for entity in message.entities:
                # Keep only formatting entities, remove others (like mentions from forward)
                if isinstance(entity, (types.MessageEntityBold, types.MessageEntityItalic, 
                                     types.MessageEntityCode, types.MessageEntityPre, 
                                     types.MessageEntityTextUrl)):
                    entities.append(entity)

        # Handle different message types
        if message.media and not (message.web_preview and is_from_bot):
            # Media message
            if caption:
                await client.send_file(chat_id, message.media, caption=caption, entities=entities)
            else:
                await client.send_file(chat_id, message.media)
            logger.info(f"Media message forwarded to {chat_id}")
        elif caption:
            # Text message
            await client.send_message(chat_id, caption, entities=entities)
            logger.info(f"Text message forwarded to {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Error in forward_without_tag: {str(e)}")
        # Fallback to regular forwarding
        try:
            await client.forward_messages(chat_id, message)
            logger.info(f"Message forwarded to {chat_id} with forward tag (fallback)")
            return True
        except Exception as e2:
            logger.error(f"Fallback forwarding also failed: {str(e2)}")
            return False

# Update user statistics
def update_user_stats(user_id, message_type="text", length=0):
    if user_id not in user_statistics:
        user_statistics[user_id] = {
            "message_count": 0,
            "last_message": None,
            "first_seen": datetime.now().isoformat(),
            "message_types": {"text": 0, "media": 0, "command": 0},
            "total_chars": 0,
            "avg_response_time": 0,
            "language_preference": "bengali"  # Default to Bengali
        }

    user_statistics[user_id]["message_count"] += 1
    user_statistics[user_id]["last_message"] = datetime.now().isoformat()
    user_statistics[user_id]["message_types"][message_type] += 1
    user_statistics[user_id]["total_chars"] += length

# AI API integration for unanswered questions
async def get_ai_response(message_text):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(AI_API_URL + message_text) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"AI API returned status code: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error getting AI response: {str(e)}")
        return None

# Enhanced message processing with NLP-like pattern matching and Benglish support
async def process_message(user_id, message_text, message_entities=None):
    message_text_lower = message_text.lower().strip()
    original_text = message_text

    # Initialize conversation context if not exists
    if user_id not in conversation_context:
        conversation_context[user_id] = {
            "last_message": "",
            "message_count": 0,
            "last_response": "",
            "topic": "general",
            "mood": "neutral",
            "language_preference": "bengali"
        }

    # Update conversation context
    conversation_context[user_id]["last_message"] = original_text
    conversation_context[user_id]["message_count"] += 1

    # Update user statistics
    update_user_stats(user_id, "text", len(original_text))

    # Store message in history
    message_history.append({
        "user_id": user_id,
        "text": original_text,
        "timestamp": datetime.now().isoformat(),
        "response": None  # Will be filled after response
    })

    # Check for Benglish patterns first
    benglish_intent = process_benglish_text(message_text_lower)
    if benglish_intent:
        if benglish_intent == 'how_are_you':
            return {
                "response": random.choice(how_are_you_responses),
                "priority": "low",
                "update_context": {"mood": "happy"}
            }
        elif benglish_intent == 'what_doing':
            return {
                "response": random.choice(what_are_you_doing_responses),
                "priority": "low"
            }
        elif benglish_intent == 'thanks':
            return {
                "response": random.choice(thanks_responses),
                "priority": "low",
                "update_context": {"mood": "happy"}
            }
        elif benglish_intent == 'greeting':
            greeting_time = ""
            hour = datetime.now().hour
            if 5 <= hour < 12:
                greeting_time = "সুপ্রভাত! "
            elif 12 <= hour < 16:
                greeting_time = "শুভ অপরাহ্ন! "
            elif 16 <= hour < 20:
                greeting_time = "শुভ সন্ধ্যা! "
            else:
                greeting_time = "শুভ রাত্রি! "
            return {
                "response": greeting_time + random.choice(["Hello!", "Hi there!", "হ্যালো!", "আসসালামু আলাইকুম!"]),
                "priority": "low"
            }
        elif benglish_intent == 'time_inquiry':
            current_time = datetime.now().strftime("%I:%M %p")
            current_date = datetime.now().strftime("%d %B, %Y")
            return {
                "response": f"এখন সময়: {current_time}\nআজকের তারিখ: {current_date}",
                "priority": "normal"
            }
        elif benglish_intent == 'date_inquiry':
            current_date = datetime.now().strftime("%d %B, %Y")
            day_name = datetime.now().strftime("%A")
            return {
                "response": f"আজকের তারিখ: {current_date}\nদিন: {day_name}",
                "priority": "normal"
            }
        elif benglish_intent == 'help':
            help_text = """
🤖 আমি কী করতে পারি:

- মেসেজ ফরওয়ার্ড করা
- সাধারণ কথোপকথন করা
- সময় এবং তারিখ জানানো
- ব্যবহারকারীর স্ট্যাটাস ট্র্যাক করা
- অটোমেটেড রেসপন্স দেয়া

📋 কমান্ডস:
/start - বট শুরু করুন
/status - বট স্ট্যাটাস চেক করুন
/stats - আপনার স্ট্যাটিস্টিক্স দেখুন
/help - এই মেসেজ দেখুন

আমাকে যে কোনো প্রশ্ন করতে পারেন!
"""
            return {
                "response": help_text,
                "priority": "normal"
            }
        elif benglish_intent == 'who_are_you':
            return {
                "response": "আমি একটি অটোমেটেড বট! আমি আপনার মেসেজ Manage এবং ফরওয়ার্ড করতে সাহায্য করি।",
                "priority": "normal"
            }
        elif benglish_intent == 'order_related':
            return {
                "response": "অর্ডার সম্পর্কিত তথ্য দেয়া হয়। আপনি নতুন অর্ডার দিতে বা অর্ডার চেক করতে পারেন।",
                "priority": "normal"
            }
        elif benglish_intent == 'goodbye':
            return {
                "response": random.choice(["বিদায়!", "Goodbye!", "See you later!", "আল্লাহ হাফিজ!", "শুভ রাত্রি!"]),
                "priority": "low"
            }

    # Check for specific patterns with priority
    # Emergency or urgent messages
    if re.search(r'\b(জরুরী|紧急|urgent|emergency|help me|বাঁচাও|সাহায্য)\b', message_text_lower, re.IGNORECASE):
        return {
            "response": "⚠️ জরুরী সাহায্যের প্রয়োজন? দয়া করে সরাসরি ফোন করুন বা স্থানীয় কর্তৃপক্ষের সাথে যোগাযোগ করুন। আমি শুধু একটি বট, জরুরী অবস্থায় সাহায্য করতে পারব না।",
            "priority": "high",
            "notify_admin": True
        }

    # Name inquiry
    if re.search(r'(তোমার নাম কি|কে তুমি|who are you|your name|তুমি কে|বটের নাম|your identity)', message_text_lower):
        return {
            "response": "আমি একটি অটোমেটেড বট! আমি আপনার মেসেজ Manage এবং ফরওয়ার্ড করতে সাহায্য করি।",
            "priority": "normal"
        }

    # Time inquiry
    elif re.search(r'(কটা বাজে|সময় কটা|time|কোন সময়|কত বাজে|current time|সময়)', message_text_lower):
        current_time = datetime.now().strftime("%I:%M %p")
        current_date = datetime.now().strftime("%d %B, %Y")
        return {
            "response": f"এখন সময়: {current_time}\nআজকের তারিখ: {current_date}",
            "priority": "normal"
        }

    # Date inquiry
    elif re.search(r'(আজকের তারিখ|date|ক তারিখ|কোন তারিখ|today\'s date)', message_text_lower):
        current_date = datetime.now().strftime("%d %B, %Y")
        day_name = datetime.now().strftime("%A")
        return {
            "response": f"আজকের তারিখ: {current_date}\nদিন: {day_name}",
            "priority": "normal"
        }

    # Help request
    elif re.search(r'(সাহায্য|help|হেল্প|কাজ কি|what can you do|কি করতে পারো|ফিচার|features)', message_text_lower):
        help_text = """
🤖 আমি কী করতে পারি:

- মেসেজ ফরওয়ার্ড করা
- সাধারণ কথোপকথন করা
- সময় এবং তারিখ জানানো
- ব্যবহারকারীর স্ট্যাটাস ট্র্যাক করা
- অটোমেটেড রেসপন্স দেয়া

📋 কমান্ডস:
/start - বট শুরু করুন
/status - বট স্ট্যাটাস চেক করুন
/stats - আপনার স্ট্যাটিস্টিক্স দেখুন
/help - এই মেসেজ দেখুন

আমাকে যে কোনো প্রশ্ন করতে পারেন!
"""
        return {
            "response": help_text,
            "priority": "normal"
        }

    # Greetings
    elif any(greet in message_text_lower for greet in greetings):
        greeting_time = ""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting_time = "সুপ্রভাত! "
        elif 12 <= hour < 16:
            greeting_time = "শুভ অপরাহ্ন! "
        elif 16 <= hour < 20:
            greeting_time = "শুভ সন্ধ্যা! "
        else:
            greeting_time = "শুভ রাত্রি! "
        return {
            "response": greeting_time + random.choice(["Hello!", "Hi there!", "হ্যালো!", "আসসালামু আলাইকুম!"]),
            "priority": "low"
        }

    # How are you
    elif re.search(r'(কেমন আছো|কেমন আছেন|খবর কি|কি খবর|কেমন আছে|how are you|how do you do)', message_text_lower):
        # Vary response based on conversation history
        mood = conversation_context[user_id].get("mood", "neutral")
        if mood == "happy":
            responses = ["অসাধারণ ভালো আছি! আপনার জন্য কি করতে পারি?", "খুব ভালো, ধন্যবাদ! আপনার দিনটি ভালো যাচ্ছে তো?"]
        else:
            responses = how_are_you_responses
        return {
            "response": random.choice(responses),
            "priority": "low",
            "update_context": {"mood": "happy"}
        }

    # What are you doing
    elif re.search(r'(কি করছো|কি করছেন|কী করছ|কি করতেছ|কাজ কি|what are you doing|what are you up to)', message_text_lower):
        return {
            "response": random.choice(what_are_you_doing_responses),
            "priority": "low"
        }

    # Thanks
    elif re.search(r'(ধন্যবাদ|থ্যাংকস|thank you|thanks|শুকরিয়া|thankyou|appreciate)', message_text_lower):
        return {
            "response": random.choice(thanks_responses),
            "priority": "low",
            "update_context": {"mood": "happy"}
        }

    # Goodbye
    elif re.search(r'(bye|goodbye|বিদায়|see you|allah hafiz|good night|শুভ রাত্রি)', message_text_lower):
        return {
            "response": random.choice(["বিদায়!", "Goodbye!", "See you later!", "আল্লাহ হাফিজ!", "শুভ রাত্রি!"]),
            "priority": "low"
        }

    # Order related
    elif re.search(r'(order|অর্ডার|order korbo|order dete|order debo)', message_text_lower):
        return {
            "response": "অর্ডার সম্পর্কিত তথ্য দেয়া হয়। আপনি নতুন অর্ডার দিতে বা অর্ডার চেক করতে পারেন।",
            "priority": "normal"
        }

    # Forward status check
    elif re.search(r'(ফরওয়ার্ড|ফরওয়ার্ডিং|forward|check status|স্ট্যাটাস)', message_text_lower):
        return {
            "response": "✅ ফরওয়ার্ড সিস্টেম এক্টিভ আছে। সকল মেসেজ ফরওয়ার্ড করা হবে। কোনো সমস্যা হলে অ্যাডমিনকে জানান।",
            "priority": "normal"
        }

    # User asking to talk to a human
    elif re.search(r'(হিউম্যান|human|person|ব্যক্তি|অ্যাডমিন|admin|সাপোর্ট|support)', message_text_lower):
        return {
            "response": "দুঃখিত, এখন কোনো অ্যাডমিন অবশিষ্ট নেই। আপনার মেসেজ রেকর্ড করা হয়েছে এবং একজন অ্যাডমিন ASAP রেসপন্ড করবেন। জরুরী প্রয়োজন হলে দয়া করে ফোন করুন।",
            "priority": "high",
            "notify_admin": True
        }

    # If nothing matches, use AI API
    else:
        # If the same user sends multiple unknown messages
        msg_count = conversation_context[user_id]["message_count"]
        if msg_count > 5:
            return {
                "response": "আমি দেখতে পাচ্ছি আপনি বেশ কয়েকবার মেসেজ করেছেন। আমি এখনো অনেক কিছু শিখিনি। আপনি কি অন্য কোনো বিষয়ে সাহায্য প্রয়োজন?",
                "priority": "normal"
            }
        elif msg_count > 3:
            return {
                "response": "আমি এখনো অনেক কিছু শিখিনি। আপনি কি অর্ডার দিতে চান?",
                "priority": "normal"
            }
        else:
            # Use AI API for responses
            ai_response = await get_ai_response(message_text)
            if ai_response:
                return {
                    "response": ai_response,
                    "priority": "normal",
                    "ai_generated": True
                }
            else:
                return {
                    "response": random.choice(unknown_responses),
                    "priority": "low"
                }

# Update user status with more details
def update_user_status(user_id, status, message_count=0):
    user_status[user_id] = {
        "status": status,
        "timestamp": time.time(),
        "last_updated": datetime.now().isoformat(),
        "message_count": message_count
    }

    # Also update activity tracking
    if user_id not in user_activity:
        user_activity[user_id] = []
    
    user_activity[user_id].append({
        "action": status,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 100 activities per user
    if len(user_activity[user_id]) > 100:
        user_activity[user_id] = user_activity[user_id][-100:]

# Get user info with caching
async def get_user_info(user_id):
    try:
        user = await client.get_entity(user_id)
        return user
    except Exception as e:
        logger.error(f"Error getting user info for {user_id}: {str(e)}")
        return None

# Scheduled backup task
async def scheduled_backup():
    while True:
        await asyncio.sleep(BACKUP_INTERVAL)
        try:
            save_data()
            logger.info("Data backup completed successfully.")

            # Send backup status to admin (once a day)
            now = datetime.now()
            if now.hour == 2 and now.minute < 5:  # Around 2 AM
                for admin_id in ADMIN_USER_IDS:
                    try:
                        stats_summary = f"📊 বট স্ট্যাটাস:\n- ইউজার: {len(user_statistics)}\n- মেসেজ হিস্টরি: {len(message_history)}\n- কনভারসেশন: {len(conversation_context)}"
                        await client.send_message(admin_id, f"🔄 অটো ব্যাকআপ সম্পন্ন\n{stats_summary}")
                    except Exception as e:
                        logger.error(f"Could not send backup status to admin {admin_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in scheduled backup: {str(e)}")

# Cleanup old data task
async def cleanup_old_data():
    while True:
        await asyncio.sleep(86400)  # Run once per day
        try:
            # Cleanup message history older than 30 days
            global message_history
            now = datetime.now()
            message_history = [msg for msg in message_history
                             if (now - datetime.fromisoformat(msg['timestamp'])).days < 30]

            # Cleanup inactive user statistics (no message for 60 days)
            global user_statistics
            for user_id in list(user_statistics.keys()):
                last_msg = user_statistics[user_id].get('last_message')
                if last_msg and (now - datetime.fromisoformat(last_msg)).days > 60:
                    del user_statistics[user_id]
            
            save_data()
            logger.info("Old data cleanup completed.")
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")

# Handle new messages with enhanced logic
@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):
    try:
        # Get sender information
        sender = await event.get_sender()
        user_id = sender.id

        # Skip if message is from forward target user (no auto-reply)
        if user_id == FORWARD_USER_ID:
            logger.info(f"Message from forward target user {user_id}, skipping auto-reply")
            return

        # Only work in private chats
        if event.is_private:
            # Check if message is from the source bot
            if sender and ((hasattr(sender, 'username') and sender.username and 
                          sender.username.lower() == SOURCE_BOT_USERNAME.lower())):
                logger.info(f"Received message from {SOURCE_BOT_USERNAME}")
                
                # Forward message without tag to both admin and forward user
                success1 = await forward_without_tag(ADMIN_USER_ID, event.message)
                success2 = await forward_without_tag(FORWARD_USER_ID, event.message)
                
                # Notify admin for important messages
                if success1 or success2:
                    try:
                        message_text = event.message.text or ""
                        lower_text = message_text.lower()
                        
                        # Check for important keywords
                        important_keywords = ['order', 'অর্ডার', 'confirm', 'কনফার্ম', 'payment', 'পেমেন্ট', 'delivery', 'ডেলিভারি']
                        if any(keyword in lower_text for keyword in important_keywords):
                            await client.send_message(
                                ADMIN_USER_ID,
                                "🔔 **গুরুত্বপূর্ণ নোটিফিকেশন:** একটি নতুন অর্ডার বা কনফার্মেশন মেসেজ এসেছে!",
                                silent=True  # Send as silent notification
                            )
                    except Exception as e:
                        logger.error(f"Could not send notification: {str(e)}")
                return

            # Only respond if sender is not a bot and not the forward target
            if not sender.bot and user_id != FORWARD_USER_ID:
                message_text = event.raw_text
                
                # Ignore empty messages
                if not message_text or message_text.isspace():
                    return
                
                logger.info(f"Received message from {user_id}: {message_text}")
                
                # Process message with enhanced logic
                processed = await process_message(user_id, message_text, event.message.entities)
                response_message = processed.get("response")
                priority = processed.get("priority", "normal")
                notify_admin = processed.get("notify_admin", False)
                ai_generated = processed.get("ai_generated", False)
                
                # Update context if specified
                if "update_context" in processed:
                    conversation_context[user_id].update(processed["update_context"])
                
                # If there's a response, send it
                if response_message:
                    # Add typing delay based on priority and message length
                    if priority == "high":
                        delay = random.uniform(0.5, 1.5)  # Faster response for high priority
                    elif priority == "low":
                        delay = random.uniform(2.0, 5.0)  # Slower for low priority
                    else:
                        delay = random.uniform(1.0, 3.0)  # Normal
                    
                    await asyncio.sleep(delay)
                    
                    # Show typing indicator based on message length
                    async with client.action(event.chat_id, 'typing'):
                        typing_delay = len(response_message) / 20  # Adjust typing speed
                        await asyncio.sleep(min(typing_delay, 4))  # Max 4 seconds typing
                    
                    # Send the response
                    await event.reply(response_message)
                    logger.info(f"Replied to {user_id}: {response_message}")
                    
                    # Update message history with response
                    if message_history:
                        message_history[-1]["response"] = response_message
                        message_history[-1]["ai_generated"] = ai_generated
                
                # Update user status
                update_user_status(user_id, "replied", conversation_context[user_id]["message_count"])
                
                # Notify admin if needed
                if notify_admin:
                    for admin_id in ADMIN_USER_IDS:
                        try:
                            user_info = await get_user_info(user_id)
                            user_name = f"{user_info.first_name} {user_info.last_name}" if user_info else str(user_id)
                            await client.send_message(
                                admin_id,
                                f"👤 ইউজার নোটিফিকেশন:\n{user_name} জরুরী সাহায্য চেয়েছেন:\n\"{message_text}\""
                            )
                        except Exception as e:
                            logger.error(f"Could not send admin notification: {str(e)}")
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")

# Handle user updates with more details
@client.on(events.UserUpdate)
async def handle_user_update(event):
    try:
        user = await event.get_user()
        if user.status:
            status_text = ""
            if isinstance(user.status, UserStatusOnline):
                status_text = "online"
            elif isinstance(user.status, UserStatusOffline):
                status_text = f"offline (last seen: {user.status.was_online})"
            elif isinstance(user.status, UserStatusRecently):
                status_text = "recently online"
            elif isinstance(user.status, UserStatusLastWeek):
                status_text = "last seen within a week"
            elif isinstance(user.status, UserStatusLastMonth):
                status_text = "last seen within a month"

            logger.info(f"User {user.id} status changed to: {status_text}")
            # Update user status in our tracking
            update_user_status(user.id, status_text)
    except Exception as e:
        logger.error(f"Error in user update: {str(e)}")

# Enhanced command handlers
@client.on(events.NewMessage(pattern='/start'))
async def start_command_handler(event):
    try:
        if event.is_private:
            sender = await event.get_sender()
            # Don't auto-reply to forward target user
            if not sender.bot and sender.id != FORWARD_USER_ID:
                welcome_text = """
🤖 স্বাগতম!

আমি একটি অটোমেটেড বট যা আপনাকে সাহায্য করতে এখানে আছি।

📋 আমি যা করতে পারি:

- মেসেজ ফরওয়ার্ড করা
- সাধারণ কথোপকথন করা
- সময় এবং তারিখ জানানো
- আপনার প্রশ্নের উত্তর দেওয়া

❓ সাহায্যের জন্য /help লিখুন
📊 স্ট্যাটাস চেক করতে /status লিখুন

আমাকে যে কোনো প্রশ্ন করতে পারেন!
"""
                await event.reply(welcome_text)
                logger.info(f"Start command executed by {sender.id}")
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")

@client.on(events.NewMessage(pattern='/status'))
async def status_command_handler(event):
    try:
        if event.is_private:
            sender = await event.get_sender()
            # Don't auto-reply to forward target user
            if not sender.bot and sender.id != FORWARD_USER_ID:
                # Get bot info
                me = await client.get_me()

                # Calculate uptime (if available)
                uptime = "Unknown"
                if 'start_time' in globals():
                    uptime_seconds = int(time.time() - globals()['start_time'])
                    uptime = f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m"

                status_message = f"""
🤖 বট স্ট্যাটাস:

সিস্টেম:
বট: {me.first_name} (ID: {me.id})
আপটাইম: {uptime}
সার্ভার সময়: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

পরিসংখ্যান:
ইউজার: {len(user_statistics)}
মেসেজ হ্যান্ডেল্ড: {len(message_history)}
সক্রিয় কনভারসেশন: {len([v for v in conversation_context.values() if v['message_count'] > 0])}

কনফিগারেশন:
অ্যাডমিন: {ADMIN_USER_ID}
ফরওয়ার্ড ইউজার: {FORWARD_USER_ID}
অ্যাডমিন: {len(ADMIN_USER_IDS)} জন
"""

                await event.reply(status_message)
                logger.info(f"Status command executed by {sender.id}")
    except Exception as e:
        logger.error(f"Error in status command: {str(e)}")

@client.on(events.NewMessage(pattern='/stats'))
async def stats_command_handler(event):
    try:
        if event.is_private:
            sender = await event.get_sender()
            # Don't auto-reply to forward target user
            if not sender.bot and sender.id != FORWARD_USER_ID:
                user_id = sender.id

                if user_id in user_statistics:
                    stats = user_statistics[user_id]
                    first_seen = datetime.fromisoformat(stats['first_seen']).strftime('%Y-%m-%d %H:%M')
                    last_message = datetime.fromisoformat(stats['last_message']).strftime('%Y-%m-%d %H:%M') if stats['last_message'] else "Never"
                    
                    stats_message = f"""
📊 আপনার পরিসংখ্যান:

প্রথম দেখা: {first_seen}
শেষ মেসেজ: {last_message}
মোট মেসেজ: {stats['message_count']}
টেক্সট মেসেজ: {stats['message_types']['text']}
মিডিয়া মেসেজ: {stats['message_types']['media']}
কমান্ড: {stats['message_types']['command']}
গড় রেসপন্স সময়: {stats.get('avg_response_time', 'N/A')}s
"""

                    await event.reply(stats_message)
                    logger.info(f"Stats command executed by {user_id}")
                else:
                    await event.reply("❌ আপনার কোনো পরিসংখ্যান পাওয়া যায়নি। আপনি এখনো কোনো মেসেজ পাঠাননি।")
    except Exception as e:
        logger.error(f"Error in stats command: {str(e)}")

@client.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_command_handler(event):
    try:
        if event.is_private:
            sender = await event.get_sender()
            # Only allow admins to broadcast
            if sender.id in ADMIN_USER_IDS:
                # Extract broadcast message (text after /broadcast)
                broadcast_text = event.raw_text.split(' ', 1)[1] if ' ' in event.raw_text else None

                if not broadcast_text:
                    await event.reply("❌ ব্রডকাস্ট করার জন্য মেসেজ প্রয়োজন। ব্যবহার: /broadcast <message>")
                    return

                # Confirm broadcast
                confirm_msg = await event.reply(f"⚠️ এই মেসেজটি {len(user_statistics)} জন ইউজারকে পাঠানো হবে:\n\n{broadcast_text}\n\nকনফার্ম করতে 'yes' লিখুন।")

                # Wait for confirmation
                try:
                    response = await client.wait_for(
                        events.NewMessage(from_users=sender.id, chat_id=event.chat_id),
                        timeout=30.0
                    )
                    
                    if response.text.lower() == 'yes':
                        # Send broadcast to all users
                        success_count = 0
                        fail_count = 0
                        
                        await event.reply("🔄 ব্রডকাস্ট শুরু হচ্ছে...")
                        
                        for user_id in user_statistics.keys():
                            try:
                                await client.send_message(user_id, f"📢 **ব্রডকাস্ট:**\n\n{broadcast_text}")
                                success_count += 1
                                await asyncio.sleep(0.5)  # Rate limiting
                            except Exception as e:
                                logger.error(f"Failed to send broadcast to {user_id}: {str(e)}")
                                fail_count += 1
                        
                        await event.reply(f"✅ ব্রডকাস্ট সম্পন্ন!\nসফল: {success_count}\nব্যর্থ: {fail_count}")
                    else:
                        await event.reply("❌ ব্রডকাস্ট বাতিল করা হয়েছে。")
                except asyncio.TimeoutError:
                    await event.reply("❌ ব্রডকাস্ট কনফার্মেশন টাইমআউট। ব্রডকাস্ট বাতিল করা হয়েছে。")
                
                logger.info(f"Broadcast command executed by {sender.id}")
            else:
                await event.reply("❌ আপনার এই কমান্ড ব্যবহার করার অনুমতি নেই。")
    except Exception as e:
        logger.error(f"Error in broadcast command: {str(e)}")

# Initialize and start the client
async def main():
    # Load existing data
    load_data()

    # Start the client
    await client.start()
    logger.info("Enhanced auto-replying and forwarding client started...")
    
    # Store start time for uptime calculation
    globals()['start_time'] = time.time()
    
    # Get bot info
    me = await client.get_me()
    logger.info(f"Logged in as {me.first_name} (ID: {me.id})")
    
    # Start background tasks
    asyncio.create_task(scheduled_backup())
    asyncio.create_task(cleanup_old_data())
    
    # Send startup message to admin
    for admin_id in ADMIN_USER_IDS:
        try:
            await client.send_message(
                admin_id,
                f"🤖 বট সফলভাবে শুরু হয়েছে!\n\n"
                f"- লগইন: {me.first_name} (ID: {me.id})\n"
                f"- সময়: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"- লোডেড ইউজার: {len(user_statistics)} জন\n"
                f"- ফরওয়ার্ড ইউজার: {FORWARD_USER_ID}\n\n"
                f"স্ট্যাটাস চেক করতে /status কমান্ড ব্যবহার করুন।"
            )
        except Exception as e:
            logger.error(f"Could not send startup message to admin {admin_id}: {str(e)}")
    
    # Run until disconnected
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        # Save data before exit
        save_data()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        logger.info("Bot stopped!")