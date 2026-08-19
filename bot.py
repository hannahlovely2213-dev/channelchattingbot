import asyncio
import logging
import random
import os
import json
from datetime import datetime
from typing import List, Tuple
import pytz
import sys
import signal

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Suppress httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)

# Environment variables
BOT_TOKEN_A = os.environ.get('BOT_TOKEN_A')
BOT_TOKEN_B = os.environ.get('BOT_TOKEN_B')

if not BOT_TOKEN_A or not BOT_TOKEN_B:
    logger.error("Please set BOT_TOKEN_A and BOT_TOKEN_B environment variables")
    sys.exit(1)

# File to store group chat IDs
GROUP_FILE = 'group_chats.json'

# Conversation pairs
CONVERSATION_PAIRS: List[Tuple[str, str]] = [
    ("Did you know you can earn passive income through crypto staking? Some platforms offer up to 3.5% daily returns! 💰", 
     "That's impressive! I've been looking into passive income opportunities myself. The VIP program seems especially promising with those rates."),
    ("The crypto market is showing strong bullish signals this week. Perfect timing for new investors to join! 📈", 
     "Absolutely! I've noticed the momentum too. The team behind this project seems very professional and dedicated."),
    ("Financial freedom is achievable when you have the right strategy and team support. Our community is growing fast! 🚀", 
     "Couldn't agree more! I've seen so many success stories already. The team leader program adds an extra layer of opportunity."),
    ("Market analysis shows we're entering a new growth phase. Early adopters will benefit the most! ⏰", 
     "That's exactly why I joined when I did. The timing couldn't be better for those ready to take action."),
    ("Teamwork makes the dream work! Our community members are achieving amazing results together. 🌟", 
     "The community spirit here is incredible! Everyone helps each other succeed. That's rare to find."),
    ("Crypto education is key to long-term success. We provide comprehensive training for all members. 📚", 
     "The educational resources are top-notch! I've learned so much since joining. It makes all the difference."),
    ("Daily compounding can turn small investments into significant wealth over time. 📊", 
     "The compounding effect is real! I've been tracking my returns and they're consistently impressive."),
    ("Our VIP members enjoy exclusive benefits and higher returns. It's the best way to maximize earnings! 👑", 
     "I upgraded to VIP last week and it's been game-changing. The extra 3.5% really adds up!"),
    ("The crypto space is evolving rapidly. Being part of a strong community gives you an edge. 🌐", 
     "Community is everything in this space. Our group shares insights and strategies daily."),
    ("Financial growth requires consistency and patience. Our system makes it easy to stay on track. 📈", 
     "Consistency is key! I've developed a routine and it's paying off beautifully."),
    ("Global markets are showing increased institutional interest in crypto. Big things coming! 🌍", 
     "I've been reading about that too! The institutional adoption is accelerating rapidly."),
    ("Referral bonuses are an excellent way to build your team and increase earnings. 🎯", 
     "I've been sharing my referral link and already seeing results! The bonuses are generous."),
    ("Security is our top priority. Your investments are safe with our platform. 🔒", 
     "Security was my main concern initially. But their security measures are industry-leading."),
    ("Our support team is available 24/7 to help with any questions or issues. 🎧", 
     "The support is amazing! Any time I've had a question, they've responded immediately."),
    ("Team leaders earn up to 0.6% commission on their team's activity. That's substantial! 💰", 
     "I'm working towards becoming a team leader myself. The commission structure is very attractive."),
]

# Promotional text
PROMOTIONAL_TEXT = """
✅ VIP has increased to 3.5% + 3📌

🪙 REGISTER HERE ⏩⏩

https://app-web.mobiuspe-app.com/regist?code=earnmoney426

✅ We offer team leader salaries and up to 0.6% team commission. Please contact us to apply for a team leader position. 🛒
Official channel link ⭐️

https://t.me/mobiuspayofficial1

Contact support ⭐️@puya1521
"""

FOLLOW_UP_TEXT = "What are you waiting for? Click the link above and start earning today! If you have questions, our support team @puya1521 is ready to help."


class GroupManager:
    def __init__(self, filename: str = GROUP_FILE):
        self.filename = filename
        self.groups: List[int] = []
        self.load_groups()
    
    def load_groups(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    self.groups = json.load(f)
                logger.info(f"Loaded {len(self.groups)} groups from {self.filename}")
            else:
                self.groups = []
                logger.info(f"No existing group file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading groups: {e}")
            self.groups = []
    
    def save_groups(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.groups, f)
            logger.info(f"Saved {len(self.groups)} groups to {self.filename}")
        except Exception as e:
            logger.error(f"Error saving groups: {e}")
    
    def add_group(self, chat_id: int):
        if chat_id not in self.groups:
            self.groups.append(chat_id)
            self.save_groups()
            logger.info(f"Added group {chat_id} (total: {len(self.groups)})")
    
    def remove_group(self, chat_id: int):
        if chat_id in self.groups:
            self.groups.remove(chat_id)
            self.save_groups()
            logger.info(f"Removed group {chat_id} (remaining: {len(self.groups)})")
    
    def get_groups(self) -> List[int]:
        return self.groups.copy()


class BotManager:
    def __init__(self, token_a: str, token_b: str):
        self.token_a = token_a
        self.token_b = token_b
        self.group_manager = GroupManager()
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.shutdown_requested = False
        
        # Build applications
        self.app_a = self.build_application(token_a, "BotA")
        self.app_b = self.build_application(token_b, "BotB")
        
        # Store bot info
        self.bot_a_username = None
        self.bot_b_username = None
    
    def build_application(self, token: str, bot_name: str) -> Application:
        application = Application.builder().token(token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("test", self.handle_test_command))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_member))
        application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        return application
    
    async def initialize(self):
        """Initialize both applications"""
        logger.info("Initializing bots...")
        
        try:
            # Get bot info
            bot_a_info = await self.app_a.bot.get_me()
            bot_b_info = await self.app_b.bot.get_me()
            self.bot_a_username = bot_a_info.username
            self.bot_b_username = bot_b_info.username
            logger.info(f"Bot A: @{self.bot_a_username} (ID: {bot_a_info.id})")
            logger.info(f"Bot B: @{self.bot_b_username} (ID: {bot_b_info.id})")
            
            # Initialize applications
            await self.app_a.initialize()
            await self.app_b.initialize()
            
            await self.app_a.start()
            await self.app_b.start()
            
            # Start polling
            logger.info("Starting polling for Bot A...")
            await self.app_a.updater.start_polling()
            
            logger.info("Starting polling for Bot B...")
            await self.app_b.updater.start_polling()
            
            # Set up scheduler
            self.setup_scheduler()
            logger.info("✅ Both bots initialized and running successfully")
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}", exc_info=True)
            raise
    
    def setup_scheduler(self):
        self.scheduler.add_job(
            self.run_daily_session,
            CronTrigger(hour=10, minute=0, timezone=pytz.UTC),
            id='daily_session',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Scheduler started with daily session at 10:00 UTC")
    
    async def shutdown(self):
        logger.info("Shutting down bot system...")
        self.shutdown_requested = True
        
        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
            
            if self.app_a and hasattr(self.app_a, 'updater'):
                await self.app_a.updater.stop()
            
            if self.app_b and hasattr(self.app_b, 'updater'):
                await self.app_b.updater.stop()
            
            if self.app_a:
                await self.app_a.stop()
            
            if self.app_b:
                await self.app_b.stop()
            
            if self.app_a:
                await self.app_a.shutdown()
            
            if self.app_b:
                await self.app_b.shutdown()
            
            logger.info("✅ Bot system shut down successfully")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    async def send_message(self, app: Application, chat_id: int, text: str, bot_name: str):
        """Send a message and log the result"""
        try:
            await app.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            logger.info(f"✅ {bot_name} sent message to {chat_id}")
            return True
        except Exception as e:
            logger.error(f"❌ {bot_name} failed to send message to {chat_id}: {e}")
            return False
    
    async def handle_test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /test command"""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        logger.info(f"Test command received from {user.username} in chat {chat_id}")
        
        # Check if it's a group chat
        if update.effective_chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("This command only works in group chats.")
            return
        
        # Ensure group is saved
        self.group_manager.add_group(chat_id)
        
        # Send initial response
        await update.message.reply_text("🧪 Starting test session...")
        logger.info(f"Test command acknowledged for group {chat_id}")
        
        try:
            # Run mini session
            await self.run_conversation_session(chat_id, is_test=True)
            
            # Send promotional text and follow-up
            logger.info(f"Sending promotional text to group {chat_id}")
            await self.send_message(self.app_a, chat_id, PROMOTIONAL_TEXT, "BotA")
            
            await asyncio.sleep(3)
            
            logger.info(f"Sending follow-up to group {chat_id}")
            await self.send_message(self.app_b, chat_id, FOLLOW_UP_TEXT, "BotB")
            
            await update.message.reply_text("✅ Test session completed!")
            logger.info(f"✅ Test session completed for group {chat_id}")
            
        except Exception as e:
            logger.error(f"❌ Error in test session: {e}", exc_info=True)
            await update.message.reply_text("❌ Test session encountered an error. Check logs.")
    
    async def handle_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when the bot is added to a group"""
        chat_id = update.effective_chat.id
        
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                self.group_manager.add_group(chat_id)
                logger.info(f"Bot {context.bot.username} added to group {chat_id}")
                
                # Determine which bot this is
                bot_name = "BotA" if context.bot.username == self.bot_a_username else "BotB"
                
                # Send welcome message
                welcome_msg = f"👋 Thanks for adding me!\n\nI'll be here to share valuable insights about crypto earning opportunities.\n\nType /test to see a demo conversation!"
                
                # Only send welcome from Bot A to avoid duplicates
                if bot_name == "BotA":
                    await self.send_message(self.app_a, chat_id, welcome_msg, bot_name)
                break
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        
        if update.message.left_chat_member.id == context.bot.id:
            self.group_manager.remove_group(chat_id)
            logger.info(f"Bot {context.bot.username} removed from group {chat_id}")
    
    def get_daily_pairs(self) -> List[Tuple[str, str]]:
        import datetime
        seed = datetime.datetime.now().strftime("%Y%m%d")
        random.seed(seed)
        pairs = CONVERSATION_PAIRS.copy()
        random.shuffle(pairs)
        return pairs[:15]
    
    async def run_conversation_session(self, chat_id: int, is_test: bool = False):
        """Run a conversation session"""
        self.is_running = True
        
        try:
            pairs = self.get_daily_pairs()
            
            if is_test:
                wait_between_messages = 5
                wait_between_pairs = 5
                max_pairs = 3
            else:
                wait_between_messages = random.randint(60, 180)
                wait_between_pairs = random.randint(60, 180)
                max_pairs = len(pairs)
            
            logger.info(f"Starting conversation session with {min(max_pairs, len(pairs))} pairs")
            
            for i in range(min(max_pairs, len(pairs))):
                if self.shutdown_requested:
                    break
                
                msg_a, msg_b = pairs[i]
                
                # Bot A sends message
                logger.info(f"BotA sending message {i+1} to {chat_id}")
                await self.send_message(self.app_a, chat_id, msg_a, "BotA")
                
                await asyncio.sleep(wait_between_messages)
                
                if self.shutdown_requested:
                    break
                
                # Bot B replies
                logger.info(f"BotB sending reply {i+1} to {chat_id}")
                await self.send_message(self.app_b, chat_id, msg_b, "BotB")
                
                if i < min(max_pairs, len(pairs)) - 1:
                    await asyncio.sleep(wait_between_pairs)
            
            logger.info(f"Conversation session completed for {chat_id}")
            
        except Exception as e:
            logger.error(f"Error in conversation session: {e}", exc_info=True)
        finally:
            self.is_running = False
    
    async def run_daily_session(self):
        if self.is_running or self.shutdown_requested:
            return
        
        groups = self.group_manager.get_groups()
        if not groups:
            logger.info("No groups available for daily session")
            return
        
        logger.info(f"Starting daily session for {len(groups)} groups")
        
        for chat_id in groups:
            if self.shutdown_requested:
                break
            
            try:
                await self.run_conversation_session(chat_id, is_test=False)
                
                if self.shutdown_requested:
                    break
                
                logger.info(f"Sending promotional text to {chat_id}")
                await self.send_message(self.app_a, chat_id, PROMOTIONAL_TEXT, "BotA")
                
                await asyncio.sleep(3)
                
                if self.shutdown_requested:
                    break
                
                logger.info(f"Sending follow-up to {chat_id}")
                await self.send_message(self.app_b, chat_id, FOLLOW_UP_TEXT, "BotB")
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in daily session for group {chat_id}: {e}", exc_info=True)
        
        logger.info("Daily session completed")


async def main():
    logger.info("="*60)
    logger.info("🚀 Starting Telegram Bot System")
    logger.info("="*60)
    
    manager = BotManager(BOT_TOKEN_A, BOT_TOKEN_B)
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(manager.shutdown())
    
    signal.signal(signal.SIGTERM, lambda s, f: signal_handler())
    signal.signal(signal.SIGINT, lambda s, f: signal_handler())
    
    try:
        await manager.initialize()
        
        logger.info("="*60)
        logger.info("✅ Bot system is running and ready!")
        logger.info("📌 Add both bots to your group and use /test to verify")
        logger.info("⏰ Daily sessions will run at 10:00 AM UTC")
        logger.info("="*60)
        
        while not manager.shutdown_requested:
            await asyncio.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        if not manager.shutdown_requested:
            await manager.shutdown()
        logger.info("Bot system stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
