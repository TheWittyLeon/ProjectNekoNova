import os
import time
import requests
import asyncio
import twitchio
import sqlite3
import aiohttp  # For asynchronous HTTP requests
from twitch_rpg_game import RPGHandler
from twitchio.ext import commands
from dotenv import load_dotenv
from collections import deque
from datetime import datetime, timedelta
from blackjack_game import BlackjackGame  # Import the blackjack game

# Load Twitch credentials from .env
load_dotenv()
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL")
AI_API_URL = "http://localhost:8080/twitchgenerate"
LEONS_AI_API_URL = "http://localhost:8080/generate"

# Define Bot class
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TWITCH_TOKEN,
            prefix="~",
            initial_channels=[TWITCH_CHANNEL]
        )
        self.is_active = False  # Default to inactive

        # Initialize attributes
        self.user_last_request = {}  # Track user requests for rate limiting
        self.cooldown_seconds = 10  # Each user must wait this many seconds between requests
        self.message_queue = deque(maxlen=10)  # Queue system for processing messages
        self.processing = False  # Track if the bot is processing messages
        self.recent_messages = []  # Track conversation history
        self.max_history = 5  # Maximum number of recent messages to store

        # Initialize blackjack game
        self.blackjack = BlackjackGame()

        # Initialize RPG handler
        self.rpg_handler = RPGHandler("blackjack.db")

    async def poll_bot_status(self):
        """Periodically poll the API for the bot's active status."""
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:8080/bot/status") as response:
                        if response.status == 200:
                            data = await response.json()
                            new_status = data.get("status") == "active"
                            if self.is_active != new_status:
                                self.is_active = new_status
                                print(f"Bot active status updated: {'active' if self.is_active else 'inactive'}")
            except Exception as e:
                print(f"Error polling bot status: {e}")
            await asyncio.sleep(5)  # Poll every 5 seconds

    async def event_ready(self):
        print(f"✅ Bot is ready and connected as {self.nick}")
        # Start polling the bot status
        asyncio.create_task(self.poll_bot_status())

    # Raid event handler
    async def event_raid(self, event):
        print(f"🎉 Raid event received: {event}")
        # Send a message to the channel where the raid occurred
        await event.channel.send(f"🎉 Thank you, {event.raider.name}, for the raid with {event.viewer_count} viewers! 🎉")

    # Simulates a raid
    @commands.command(name='testraid')
    async def test_raid(self, ctx):
        # Restrict access to the channel owner or a specific user
        allowed_users = [TWITCH_CHANNEL.lower(), "thewittyleon"]
        if ctx.author.name.lower() not in allowed_users:
            await ctx.send(f"Sorry {ctx.author.name}, you don't have permission to use this command.")
            return

        # Fake data for simulation
        class FakeEvent:
            def __init__(self, channel, raider_name, viewer_count):
                self.channel = channel
                self.raider = type('Raider', (object,), {'name': raider_name})
                self.viewer_count = viewer_count

        # Create a fake event with the current channel, a raider name, and viewer count
        fake_event = FakeEvent(ctx.channel, "TestRaider", 42)
        await self.event_raid(fake_event)

    async def event_message(self, message):
        # Ignore messages if bot is not active
        if not self.is_active:
            # Still process admin commands to activate the bot
            if message.content.lower().startswith(f"{self._prefix}admin"):
                await self.handle_commands(message)
            return

        # Ignore messages from the bot itself or messages without an author
        if message.author is None or message.author.name.lower() == self.nick.lower():
            return

        # Process commands with the prefix
        if message.content.startswith(self._prefix):
            await self.handle_commands(message)
            return

        # Check if the message starts with 'hey Suzu'
        if message.content.lower().startswith("hey suzu"):
            author = message.author.name.lower()
            user_message = message.content[len("hey suzu"):].strip()

            # If the user just said "hey suzu" with nothing else
            if not user_message:
                await message.channel.send(f"Hi there {author}! How may I help?")
                return

            # Check if message exceeds character limit
            if len(user_message) > 400:
                await message.channel.send(f"Sorry {author}, your message is too long! Please keep it under 400 characters.")
                return

            # Check rate limit for this user
            current_time = datetime.now()
            if author in self.user_last_request:
                time_since_last = (current_time - self.user_last_request[author]).total_seconds()
                if time_since_last < self.cooldown_seconds:
                    remaining = int(self.cooldown_seconds - time_since_last)
                    await message.channel.send(f"Please wait {remaining} seconds before asking again, {author}!")
                    return

            # Update last request time for this user
            self.user_last_request[author] = current_time

            # Add to queue and process
            self.message_queue.append((message, user_message))
            if not self.processing:
                self.processing = True
                await self.process_queue()

    async def process_queue(self):
        while self.message_queue:
            message, user_message = self.message_queue.popleft()
            author = message.author.name.lower()
            
            print(f"📩 Processing request from {author}: {user_message}")
            
            # Add to recent messages history
            self.recent_messages.append(user_message)
            if len(self.recent_messages) > self.max_history:
                self.recent_messages.pop(0)
            
            # Send message to AI API
            try:
                # Send only the current message to the API, not the history
                if author == "thewittyleon":
                    response = requests.post(
                        #LEONS_
                        AI_API_URL,
                        json={"text": user_message},
                        timeout=15  # Add timeout to prevent hanging
                    )
                else:
                    response = requests.post(
                        AI_API_URL, 
                        json={"text": user_message},
                        timeout=15  # Add timeout to prevent hanging
                    )
                
                # Check for HTTP errors
                response.raise_for_status()
                
                response_data = response.json()
                ai_response = response_data.get("response", "I'm not sure how to respond to that!")

                # Check if the response exceeds the character limit
                if len(ai_response) > 450:
                    # Split the response into chunks of up to 450 characters without splitting words
                    words = ai_response.split()
                    chunks = []
                    current_chunk = ""

                    for word in words:
                        if len(current_chunk) + len(word) + 1 > 450:  # +1 for the space
                            chunks.append(current_chunk)
                            current_chunk = word
                        else:
                            current_chunk += (" " if current_chunk else "") + word

                    if current_chunk:
                        chunks.append(current_chunk)

                    # Send each chunk as a separate message
                    for chunk in chunks:
                        await message.channel.send(chunk)
                        await asyncio.sleep(1)  # Add a small delay between messages
                else:
                    # Send Suzu's reply to the chat
                    await message.channel.send(f"{ai_response}")

                self.message_queue.clear()
                
                # Add a small delay between processing queue items to avoid rate limits
                await asyncio.sleep(2)  # Increased delay to 2 seconds
            
            except requests.exceptions.HTTPError as e:
                print(f"⚠️ HTTP Error communicating with Suzu API: {e}")
                await message.channel.send("Suzu is having trouble processing your request right now!")
            
            except requests.exceptions.Timeout:
                print(f"⚠️ Timeout error communicating with Suzu API")
                await message.channel.send("Suzu is thinking too hard and needs a moment!")
            
            except Exception as e:
                print(f"⚠️ Error communicating with Suzu API: {e}")
                # Reset the queue if we encounter a serious error
                if "Content must not exceed 500 characters" in str(e):
                    print("Character limit exceeded. Clearing queue to prevent further issues.")
                    self.message_queue.clear()
                    await message.channel.send("Suzu's brain got overloaded! Please try a simpler question.")
                else:
                    await message.channel.send("Suzu is having trouble thinking right now!")
        
        self.processing = False

    # RPG commands
    @commands.command(name="rpgstats")
    async def rpg_stats_command(self, ctx, target_user=None):
        """Check your or another user's RPG stats"""
        if target_user:
            username = target_user.lower()
        else:
            username = ctx.author.name
        
        response = self.rpg_handler.get_user_stats(username)
        await ctx.send(response)

    @commands.command(name="gainxp")
    async def gain_xp_command(self, ctx, amount: int = 0):
        """Gain XP for the current user"""
        username = ctx.author.name
        response = self.rpg_handler.gain_xp(username, amount)
        await ctx.send(response)

    @commands.command(name="buy")
    async def buy_command(self, ctx, item_name: str):
        """Buy an item"""
        username = ctx.author.name
        response = self.rpg_handler.buy_item(username, item_name)
        await ctx.send(response)

    @commands.command(name="use")
    async def use_command(self, ctx, item_name: str):
        """Use an item"""
        username = ctx.author.name
        response = self.rpg_handler.use_item(username, item_name)
        await ctx.send(response)

    @commands.command(name="roll")
    async def roll_command(self, ctx, dice_notation="1d6"):
        """Rolls dice in the format 'NdM' (e.g., 2d6, 1d20)."""
        author = ctx.author.name
        result = self.rpg_handler.roll_dice(dice_notation)

        if result is None:
            await ctx.send(f"@{author}, Invalid dice notation. Use 'NdM' (e.g., 2d6, 1d20).")
        else:
            await ctx.send(f"@{author}, rolled {dice_notation}: {result}")

    @commands.command(name="xp")
    async def xp_command(self, ctx, target_user=None):
        """Check your or another user's XP"""
        if target_user:
            username = target_user.lower()
        else:
            username = ctx.author.name
        
        response = self.rpg_handler.get_user_xp(username)
        await ctx.send(response)

    @commands.command(name="spawnmonster")
    async def spawn_monster_command(self, ctx, challenge_rating: float = None):
        """Spawn a monster for battle."""
        monster = self.rpg_handler.spawn_monster(challenge_rating)
        if not monster:
            await ctx.send("Failed to spawn a monster!")
            return

        response = self.rpg_handler.start_battle(ctx.channel.name, monster)
        await ctx.send(response)

    @commands.command(name="joinbattle")
    async def join_battle_command(self, ctx):
        """Join the current battle."""
        username = ctx.author.name
        response = self.rpg_handler.join_battle(username)
        await ctx.send(response)

    @commands.command(name="attack")
    async def attack_command(self, ctx):
        """Attack the monster."""
        username = ctx.author.name

        # Check if it's the player's turn
        current_turn = self.rpg_handler.get_next_initiative()
        print(current_turn)
        if current_turn[1] != username:
            await ctx.send(f"@{username}, it's not your turn to attack!")
            return

        response = self.rpg_handler.player_attack(username)
        await ctx.send(response)
        response = self.rpg_handler.take_turn()
        while True:
            if "to attack the monster" in response or "No battle is currently active" in response:
                break
            else:
                await asyncio.sleep(1)
                await ctx.send(response)
                response = self.rpg_handler.take_turn()
        next_initiative = self.rpg_handler.get_next_initiative()
        print(next_initiative)
        if next_initiative[0] == "monster":
            response = self.rpg_handler.monster_attack()
            await asyncio.sleep(1)
            await ctx.send(response)
            next_initiative = self.rpg_handler.get_next_initiative()
            await asyncio.sleep(1)
            await ctx.send(f"It is now {next_initiative[1]}'s turn to attack the monster!")
        else:
            next_initiative = self.rpg_handler.get_next_initiative()
            await asyncio.sleep(1)
            await ctx.send(f"It is now {next_initiative[1]}'s turn to attack the monster!")

    @commands.command(name="adminheal")
    async def admin_heal_command(self, ctx):
        """Heal all players in the current battle."""
        # Check if the command user is an admin
        admin_users = ["thewittyleon"]  # Replace with actual admin usernames
        if ctx.author.name.lower() not in [admin.lower() for admin in admin_users]:
            await ctx.send(f"@{ctx.author.name}, you don't have permission to use this command.")
            return

        # Check if a battle is active
        if not self.rpg_handler.active_battle:
            await ctx.send("No battle is currently active!")
            return

        # Heal all players in the current battle
        players = self.rpg_handler.active_battle["players"]
        if not players:
            await ctx.send("No players are in the battle to heal!")
            return

        responses = []
        for player in players:
            response = self.rpg_handler.heal_player(player)
            responses.append(response)

        # Send the healing results
        await ctx.send("\n".join(responses))

    @commands.command(name="monsterattack")
    async def monster_attack_command(self, ctx):
        """Make the monster attack a random player."""
        response = self.rpg_handler.monster_attack()
        await ctx.send(response)
        response = self.rpg_handler.take_turn()
        while True:
            if "to attack the monster" in response or "No battle is currently active" in response:
                break
            else:
                await asyncio.sleep(1)
                await ctx.send(response)
                response = self.rpg_handler.take_turn()
        next_initiative = self.rpg_handler.get_next_initiative()
        print(next_initiative)
        if next_initiative[0] == "monster":
            response = self.rpg_handler.monster_attack()
            await ctx.send(response)
        else:
            response = self.rpg_handler.get_next_initiative()
            await ctx.send(f"It is now {next_initiative[1]}'s turn to attack the monster!")

    @commands.command(name="startbattle")
    async def start_battle_command(self, ctx):
        """Start the battle after players have joined."""
        response = self.rpg_handler.start_battle_trigger()
        await ctx.send(response)

    # Blackjack commands
    @commands.command(name="blackjack")
    async def blackjack_command(self, ctx):
        """Start a new blackjack game"""
        channel = ctx.channel.name
        response = self.blackjack.start_game(channel)
        await ctx.send(response)

    @commands.command(name="bet")
    async def bet_command(self, ctx, amount: int = 10):
        """Join the blackjack game with a bet"""
        channel = ctx.channel.name
        username = ctx.author.name
        response = self.blackjack.join_game(channel, username, amount)
        await ctx.send(response)

    @commands.command(name="deal")
    async def deal_command(self, ctx):
        """Start dealing cards after betting is complete"""
        channel = ctx.channel.name
        response = self.blackjack.start_dealing(channel)
        await ctx.send(response)

    @commands.command(name="hit")
    async def hit_command(self, ctx):
        """Request another card"""
        channel = ctx.channel.name
        username = ctx.author.name
        response = self.blackjack.hit(channel, username)
        await ctx.send(response)

    @commands.command(name="stand")
    async def stand_command(self, ctx):
        """Stand with your current hand"""
        channel = ctx.channel.name
        username = ctx.author.name
        response = self.blackjack.stand(channel, username)
        await ctx.send(response)

    @commands.command(name="dealer")
    async def dealer_command(self, ctx):
        """Dealer plays their hand and determine winners"""
        channel = ctx.channel.name
        response = self.blackjack.dealer_play(channel)
        # Split long responses into multiple messages if needed
        if len(response) > 450:
            chunks = [response[i:i+450] for i in range(0, len(response), 450)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(response)

    @commands.command(name="balance")
    async def balance_command(self, ctx):
        """Check your chip balance"""
        username = ctx.author.name
        response = self.blackjack.get_balance(username)
        await ctx.send(response)

    @commands.command(name="stats")
    async def stats_command(self, ctx, target_user=None):
        """Check your or another user's blackjack stats"""
        if target_user:
            username = target_user.lower()
        else:
            username = ctx.author.name
        
        response = self.blackjack.get_stats(username)
        await ctx.send(response)

    @commands.command(name="leaderboard")
    async def leaderboard_command(self, ctx):
        """Show the blackjack leaderboard"""
        leaderboard = self.blackjack.get_leaderboard(5)
        
        if not leaderboard:
            await ctx.send("No players have played blackjack yet!")
            return
        
        response = ["🏆 Blackjack Leaderboard 🏆"]
        for i, (username, chips, wins, losses) in enumerate(leaderboard, 1):
            response.append(f"{i}. {username}: {chips} chips | W: {wins} L: {losses}")
        
        await ctx.send("\n".join(response))

    @commands.command(name="addchips")
    async def addchips_command(self, ctx, target_user=None, amount: int = 100):
        """Admin command to add chips to a user"""
        # Check if the command user is an admin (you can customize this check)
        if ctx.author.name.lower() not in ["thewittyleon"]:
            await ctx.send("You don't have permission to use this command!")
            return
        
        if not target_user:
            await ctx.send("Please specify a user to add chips to!")
            return
        
        response = self.blackjack.add_chips(target_user.lower(), amount)
        await ctx.send(response)

    @commands.command(name="daily")
    async def daily_command(self, ctx):
        """Claim daily chips (once per 24 hours)"""
        username = ctx.author.name
        
        # Check if user has claimed within 24 hours
        conn = sqlite3.connect(self.blackjack.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT timestamp FROM transactions WHERE username = ? AND type = 'daily' ORDER BY timestamp DESC LIMIT 1",
            (username,)
        )
        
        last_claim = cursor.fetchone()
        conn.close()
        
        if last_claim:
            # Convert timestamp string to datetime
            from datetime import datetime
            last_claim_time = datetime.strptime(last_claim[0], "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()
            
            # Check if 24 hours have passed
            time_diff = current_time - last_claim_time
            if time_diff.total_seconds() < 86400:  # 24 hours in seconds
                hours_left = 19 - (time_diff.total_seconds() / 3600)
                print (hours_left)
                print (time_diff.total_seconds())
                print (time_diff.total_seconds() / 3600)
                await ctx.send(f"{username}, you can claim your daily chips in {int(hours_left)} hours and {int((hours_left % 1) * 60)} minutes.")
                return
        
        # Give daily chips
        daily_amount = 100
        new_balance = self.blackjack.update_user_chips(username, daily_amount, "daily")
        await ctx.send(f"💰 {username} claimed {daily_amount} daily chips! New balance: {new_balance} chips")

    @commands.command(name="give")
    async def give_command(self, ctx, target_user=None, amount: int = 0):
        """Give chips to another user"""
        if not target_user or amount <= 0:
            await ctx.send("Usage: ~give [username] [amount]")
            return
        
        sender = ctx.author.name
        recipient = target_user.lower()
        
        # Check if sender has enough chips
        sender_chips = self.blackjack.get_user_chips(sender)
        if sender_chips < amount:
            await ctx.send(f"Sorry {sender}, you only have {sender_chips} chips.")
            return
        
        # Deduct from sender
        self.blackjack.update_user_chips(sender, -amount, "give_sent")
        
        # Add to recipient
        recipient_balance = self.blackjack.update_user_chips(recipient, amount, "give_received")
        
        await ctx.send(f"💸 {sender} gave {amount} chips to {recipient}! {recipient}'s new balance: {recipient_balance} chips")

    @commands.command(name="admin")
    async def admin_command(self, ctx, action=None):
        """Admin commands to control the bot"""
        # Check if user is an admin (you should implement proper authentication)
        admin_users = ["thewittyleon"]  # Replace with actual admin usernames
        
        if ctx.author.name.lower() not in [admin.lower() for admin in admin_users]:
            await ctx.send(f"@{ctx.author.name}, you don't have permission to use admin commands.")
            return
            
        if action == "start":
            self.is_active = True
            await ctx.send("Bot is now active and responding to commands.")
        elif action == "stop":
            self.is_active = False
            await ctx.send("Bot is now inactive and will only respond to admin commands.")
        elif action == "status":
            status = "active" if self.is_active else "inactive"
            await ctx.send(f"Bot is currently {status}.")
        else:
            await ctx.send(f"@{ctx.author.name}, valid admin commands: start, stop, status")


    @commands.command(name="help")
    async def help_command(self, ctx, page: int = 1):
        """Show blackjack commands"""
        help_pages = {
            1: [
                "🎮 Blackjack Commands 🎮",
                "~blackjack - Start a new game",
                "~bet [amount] - Join with a bet",
                "~deal - Start dealing cards",
                "~hit - Get another card",
                "~stand - Keep your current hand",
                "~double - Double your bet and take one card",
                "~insurance - Bet against dealer blackjack",
                "~check - Check if dealer has blackjack",
                "~dealer - Dealer plays and determine winners",
            ],
            2: [
                "💰 Economy Commands 💰",
                "~balance - Check your chip balance",
                "~stats - View your game statistics",
                "~leaderboard - See top players",
                "~daily - Claim daily chips",
                "~give [user] [amount] - Give chips to another user"
            ]
        }

        if page < 1 or page > len(help_pages):
            await ctx.send(f"📖 Available help pages: 1-{len(help_pages)}")
            return

        await ctx.send(f"Page {page}/{len(help_pages)}\n" + "\n".join(help_pages[page]))

# Expose the bot instance for external use
bot = Bot()

def get_bot_instance():
    return bot

def set_bot_instance(instance):
    global bot  # Declare bot as global to modify it
    bot = instance
    print(f"Bot instance set: {bot}")  # Debug log

# Run the bot
if __name__ == "__main__":
    bot.run()