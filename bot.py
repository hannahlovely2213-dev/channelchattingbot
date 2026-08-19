import asyncio
import logging
import random
import os
import json
from datetime import datetime, time
from typing import List, Tuple, Dict, Optional
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
BOT_TOKEN_A = os.environ.get('BOT_TOKEN_A')
BOT_TOKEN_B = os.environ.get('BOT_TOKEN_B')

if not BOT_TOKEN_A or not BOT_TOKEN_B:
    raise ValueError("Please set BOT_TOKEN_A and BOT_TOKEN_B environment variables")

# File to store group chat IDs
GROUP_FILE = 'group_chats.json'

# Conversation pairs - 30+ topics
CONVERSATION_PAIRS: List[Tuple[str, str]] = [
    # Crypto earning and passive income
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
    
    ("Crypto adoption is skyrocketing globally. We're at the beginning of a massive wave. 🌊", 
     "Early movers always benefit the most in new markets. This is the time to position ourselves."),
    
    ("Diversification is smart, but focusing on high-quality opportunities yields the best results. 🎯", 
     "I've been diversifying, but this platform has been my best performer by far."),
    
    ("Transparency is crucial in crypto. We provide full visibility into all operations. 👀", 
     "I appreciate the transparency! It builds trust and confidence in the platform."),
    
    ("The VIP program offers exclusive access to premium features and higher returns. 🌟", 
     "I'm enjoying the VIP benefits tremendously. The extra perks make a big difference."),
    
    ("Building a strong network leads to more opportunities and higher earnings. 🤝", 
     "Networking has been key to my success here. I've connected with amazing people."),
    
    ("Crypto winter is over! The market is heating up and opportunities are abundant. 🔥", 
     "I've been watching the charts closely. This bull run has real momentum behind it."),
    
    ("Our community is growing by hundreds of members daily. The momentum is incredible! 🚀", 
     "I noticed that too! The growth rate is phenomenal. It creates even more opportunities."),
    
    ("Regular updates and improvements keep our platform ahead of the competition. 💪", 
     "The team is constantly improving things. I appreciate their dedication to excellence."),
    
    ("Success leaves clues. Follow what works and consistently execute. 📝", 
     "I've been following the strategies shared by successful members. The results speak for themselves."),
    
    ("The future of finance is decentralized. We're building that future together. 🌅", 
     "DeFi is the future! Being part of this movement is exciting and rewarding."),
    
    ("Consistent daily earnings add up significantly over time. Start small, think big. 💡", 
     "I started with a modest investment and it's grown substantially. Daily compounding is powerful."),
    
    ("Our team provides comprehensive training and support for all members. 🎓", 
     "The training materials are excellent! They've helped me understand the market better."),
    
    ("Crypto markets operate 24/7. Our platform is always available for you. 🕐", 
     "I love that I can check my earnings anytime, anywhere. The convenience is unmatched."),
    
    ("Strategic partnerships are expanding our reach and capabilities. 🤝", 
     "I've been reading about the partnerships! They're positioning us for massive growth."),
    
    ("Every successful journey starts with a single step. Take action today! 👣", 
     "I'm so glad I took that first step. It's been life-changing for my finances."),
    
    ("The referral program rewards you for sharing opportunities with others. 🎁", 
     "My referrals are already earning! The system works great for everyone involved."),
    
    ("Team leaders receive special bonuses and recognition for their contributions. 🏆", 
     "The recognition and bonuses for team leaders are very motivating. I'm working towards it."),
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
    """Manages group chat IDs with persistent storage"""
    
    def __init__(self, filename: str = GROUP_FILE):
        self.filename = filename
        self.groups: List[int] = []
        self.load_groups()
    
    def load_groups(self):
        """Load groups from file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    self.groups = json.load(f)
                logger.info(f"Loaded {len(self.groups)} groups")
            else:
                self.groups = []
        except Exception as e:
            logger.error(f"Error loading groups: {e}")
            self.groups = []
    
    def save_groups(self):
        """Save groups to file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.groups, f)
            logger.info(f"Saved {len(self.groups)} groups")
        except Exception as e:
            logger.error(f"Error saving groups: {e}")
    
    def add_group(self, chat_id: int):
        """Add a group chat ID"""
        if chat_id not in self.groups:
            self.groups.append(chat_id)
            self.save_groups()
            logger.info(f"Added group {chat_id}")
    
    def remove_group(self, chat_id: int):
        """Remove a group chat ID"""
        if chat_id in self.groups:
            self.groups.remove(chat_id)
            self.save_groups()
            logger.info(f"Removed group {chat_id}")
    
    def get_groups(self) -> List[int]:
        """Get all group chat IDs"""
        return self.groups.copy()


class BotManager:
    """Manages the two Telegram bots and their interactions"""
    
    def __init__(self, token_a: str, token_b: str):
        self.token_a = token_a
        self.token_b = token_b
        self.group_manager = GroupManager()
        self.scheduler = AsyncIOScheduler()
        self.is_testing = False
        self.is_running = False
        
        # Build applications
        self.app_a = self.build_application(token_a, 'BotA')
        self.app_b = self.build_application(token_b, 'BotB')
        
        # Store references for message sending
        self.app_a_context = None
        self.app_b_context = None
    
    def build_application(self, token: str, bot_name: str) -> Application:
        """Build a Telegram bot application"""
        application = Application.builder().token(token).build()
        
        # Add handlers
        application.add_handler(CommandHandler("test", self.handle_test_command))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_member))
        application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, self.handle_left_member))
        
        return application
    
    async def initialize(self):
        """Initialize both applications"""
        await self.app_a.initialize()
        await self.app_b.initialize()
        await self.app_a.start()
        await self.app_b.start()
        await self.app_a.updater.start_polling()
        await self.app_b.updater.start_polling()
        
        # Set up scheduler
        self.setup_scheduler()
        logger.info("Both bots initialized and running")
    
    def setup_scheduler(self):
        """Set up the daily schedule"""
        # Schedule at 10:00 AM UTC
        self.scheduler.add_job(
            self.run_daily_session,
            CronTrigger(hour=10, minute=0, timezone=pytz.UTC),
            id='daily_session',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Scheduler started with daily session at 10:00 UTC")
    
    async def shutdown(self):
        """Properly shut down both bots"""
        try:
            # Stop polling
            await self.app_a.updater.stop()
            await self.app_b.updater.stop()
            
            # Stop applications
            await self.app_a.stop()
            await self.app_b.stop()
            
            # Shutdown
            await self.app_a.shutdown()
            await self.app_b.shutdown()
            
            logger.info("Bots shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def send_message_through_app(self, app: Application, chat_id: int, text: str):
        """Send a message using the specific application"""
        try:
            await app.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            return True
        except Exception as e:
            logger.error(f"Error sending message with {app.bot.username}: {e}")
            return False
    
    async def handle_test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /test command"""
        chat_id = update.effective_chat.id
        
        # Check if it's a group chat
        if update.effective_chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("This command only works in group chats.")
            return
        
        # Ensure group is saved
        self.group_manager.add_group(chat_id)
        
        # Notify start
        await update.message.reply_text("🧪 Starting test session...")
        
        # Run mini session
        await self.run_conversation_session(chat_id, is_test=True)
        
        # Send promotional text and follow-up
        await self.send_message_through_app(self.app_a, chat_id, PROMOTIONAL_TEXT)
        await asyncio.sleep(3)
        await self.send_message_through_app(self.app_b, chat_id, FOLLOW_UP_TEXT)
        
        await update.message.reply_text("✅ Test session completed!")
    
    async def handle_new_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when the bot is added to a group"""
        chat_id = update.effective_chat.id
        
        # Check if bot was added
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                self.group_manager.add_group(chat_id)
                logger.info(f"Bot {context.bot.username} added to group {chat_id}")
                break
    
    async def handle_left_member(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when the bot is removed from a group"""
        chat_id = update.effective_chat.id
        
        if update.message.left_chat_member.id == context.bot.id:
            self.group_manager.remove_group(chat_id)
            logger.info(f"Bot {context.bot.username} removed from group {chat_id}")
    
    def get_daily_pairs(self) -> List[Tuple[str, str]]:
        """Get conversation pairs shuffled based on daily seed"""
        # Use date as seed for consistent daily variation
        import datetime
        seed = datetime.datetime.now().strftime("%Y%m%d")
        random.seed(seed)
        
        pairs = CONVERSATION_PAIRS.copy()
        random.shuffle(pairs)
        
        # Return up to 15 pairs
        return pairs[:15]
    
    async def run_conversation_session(self, chat_id: int, is_test: bool = False):
        """Run a conversation session"""
        self.is_running = True
        
        # Get shuffled pairs
        pairs = self.get_daily_pairs()
        
        # Set intervals based on mode
        if is_test:
            wait_between_messages = 5  # 5 seconds for test
            wait_between_pairs = 5     # 5 seconds for test
        else:
            wait_between_messages = random.randint(60, 180)  # 1-3 minutes
            wait_between_pairs = random.randint(60, 180)     # 1-3 minutes
        
        try:
            for i, (msg_a, msg_b) in enumerate(pairs):
                # Bot A sends message
                logger.info(f"Sending Bot A message {i+1}/{len(pairs)} to {chat_id}")
                success = await self.send_message_through_app(self.app_a, chat_id, msg_a)
                if not success:
                    logger.error(f"Failed to send Bot A message to {chat_id}")
                    break
                
                # Wait before Bot B responds
                await asyncio.sleep(wait_between_messages)
                
                # Bot B replies
                logger.info(f"Sending Bot B reply {i+1}/{len(pairs)} to {chat_id}")
                success = await self.send_message_through_app(self.app_b, chat_id, msg_b)
                if not success:
                    logger.error(f"Failed to send Bot B message to {chat_id}")
                    break
                
                # Wait before next pair
                await asyncio.sleep(wait_between_pairs)
                
                # If test, only do 3 pairs
                if is_test and i >= 2:
                    break
        
        except Exception as e:
            logger.error(f"Error in conversation session: {e}")
        finally:
            self.is_running = False
    
    async def run_daily_session(self):
        """Run the daily scheduled session"""
        if self.is_running:
            logger.info("Session already running, skipping")
            return
        
        groups = self.group_manager.get_groups()
        if not groups:
            logger.info("No groups available for daily session")
            return
        
        logger.info(f"Starting daily session for {len(groups)} groups")
        
        for chat_id in groups:
            try:
                # Run conversation
                await self.run_conversation_session(chat_id, is_test=False)
                
                # Send promotional text
                logger.info(f"Sending promotional text to {chat_id}")
                await self.send_message_through_app(self.app_a, chat_id, PROMOTIONAL_TEXT)
                
                # Wait before follow-up
                await asyncio.sleep(3)
                
                # Send follow-up
                logger.info(f"Sending follow-up to {chat_id}")
                await self.send_message_through_app(self.app_b, chat_id, FOLLOW_UP_TEXT)
                
                # Wait between groups
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in daily session for group {chat_id}: {e}")
        
        logger.info("Daily session completed")


async def main():
    """Main entry point"""
    logger.info("Starting bot system...")
    
    # Create bot manager
    manager = BotManager(BOT_TOKEN_A, BOT_TOKEN_B)
    
    try:
        # Initialize and start bots
        await manager.initialize()
        
        # Keep running
        logger.info("Bot system is running. Press Ctrl+C to stop.")
        
        # Keep the event loop running
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour
            
    except KeyboardInterrupt:
        logger.info("Received stop signal")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Clean shutdown
        await manager.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
