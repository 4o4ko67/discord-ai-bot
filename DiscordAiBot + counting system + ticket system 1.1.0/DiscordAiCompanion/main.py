#!/usr/bin/env python3
"""
Lightweight Discord AI Bot with Ticket System
Includes AI responses (Google Gemini), counting game, ticket panel, and auto-timeout for Discord invite links.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import discord
from discord.ext import commands
from discord.ui import View, Button
from google import genai

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60
TICKET_CATEGORY_NAME = "Support Tickets"
INVITE_PATTERNS = ["discord.gg/", "discord.com/invite/", "discordapp.com/invite/"]

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN environment variable is required")
    exit(1)
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable is required")
    exit(1)

# Gemini setup
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Bot
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

# In-memory storage
user_rate_limits: Dict[int, list] = {}
counting_data: Dict[int, Dict] = {}

class RateLimiter:
    @staticmethod
    def is_rate_limited(user_id: int) -> bool:
        now = datetime.now()
        if user_id in user_rate_limits:
            user_rate_limits[user_id] = [t for t in user_rate_limits[user_id] if now - t < timedelta(seconds=RATE_LIMIT_WINDOW)]
        if len(user_rate_limits.get(user_id, [])) >= RATE_LIMIT_REQUESTS:
            return True
        user_rate_limits.setdefault(user_id, []).append(now)
        return False

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Partnership/Business Support", style=discord.ButtonStyle.danger, custom_id="ticket_partnership"))
        self.add_item(Button(label="Purchase", style=discord.ButtonStyle.primary, emoji="💰", custom_id="ticket_purchase"))
        self.add_item(Button(label="General Support", style=discord.ButtonStyle.success, custom_id="ticket_general"))

class AIResponseGenerator:
    @staticmethod
    async def generate_response(message_content: str, user_name: str) -> str:
        try:
            prompt = f"You are a helpful AI assistant.\n\n{user_name} says: {message_content}"
            response = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            text = response.text.strip() if response.text else "Sorry, I couldn't generate a response."
            return text[:MAX_MESSAGE_LENGTH] + "..." if len(text) > MAX_MESSAGE_LENGTH else text
        except Exception as e:
            logger.error(f"AI error: {e}")
            return "Sorry, I had an issue generating a response."

@bot.event
async def on_ready():
    logger.info(f"{bot.user} connected to Discord.")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="your messages | Type a message to chat!"))

@bot.event
async def on_message(message):
    if message.author.bot or message.author == bot.user:
        return

    # Invite link detection
    if any(pattern in message.content.lower() for pattern in INVITE_PATTERNS):
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                await message.author.timeout(duration=604800, reason="Posted Discord invite link")
                await message.channel.send(f"🚫 {message.author.mention} has been timed out for 7 days for sharing an invite link.")
            except Exception as e:
                logger.warning(f"Failed to timeout user: {e}")
        return

    await bot.process_commands(message)

    # Skip further checks if it's a command
    if message.content.startswith(BOT_PREFIX):
        return

    if message.content.strip().isdigit():
        await handle_counting_message(message)
        return

    mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    if not (mentioned or is_dm):
        return

    if RateLimiter.is_rate_limited(message.author.id):
        await message.reply("⏰ You're sending messages too fast. Please wait.", mention_author=False)
        return

    async with message.channel.typing():
        clean = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not clean:
            await message.reply("Hi! What would you like to talk about?", mention_author=False)
            return
        response = await AIResponseGenerator.generate_response(clean, message.author.display_name)
        await message.reply(response, mention_author=False)

async def handle_counting_message(message):
    try:
        number = int(message.content.strip())
    except ValueError:
        return

    gid = message.guild.id
    if gid not in counting_data:
        if number == 1:
            counting_data[gid] = {
                'current_number': 1,
                'last_user_id': message.author.id,
                'channel_id': message.channel.id
            }
            await message.reply(f"🎉 Game Started! {message.author.mention} typed 1. Next: 2")
            return
        else:
            await message.reply("❌ Start with 1 to begin the game!")
            return

    data = counting_data[gid]
    if data['last_user_id'] == message.author.id:
        await message.reply("❌ You can't count twice in a row!")
        return

    if number != data['current_number'] + 1:
        await message.reply(f"❌ Wrong number! Expected {data['current_number'] + 1}. Restarting from 1.")
        counting_data[gid] = {'current_number': 0, 'last_user_id': 0, 'channel_id': message.channel.id}
        return

    data['current_number'] = number
    data['last_user_id'] = message.author.id
    await message.add_reaction("✅")

@bot.command(name="ticket")
async def ticket_command(ctx):
    embed = discord.Embed(
        title="📩 Contact support!",
        description="Hello, thank you for choosing RDM! You can contact our support at any time. We are here to help you.",
        color=discord.Color.blurple()
    )
    embed.set_image(url="https://i.imgur.com/0uNL7i9.png")  # Replace with your hosted image URL
    embed.set_footer(text="Powered by RDM Support System")
    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_interaction(interaction: discord.Interaction):
    ticket_types = {
        "ticket_partnership": "partnership",
        "ticket_purchase": "purchase",
        "ticket_general": "general"
    }
    cid = interaction.data.get("custom_id")
    if cid not in ticket_types:
        return
    user = interaction.user
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        category = await guild.create_category(TICKET_CATEGORY_NAME)
    for ch in guild.text_channels:
        if ch.topic and str(user.id) in ch.topic:
            await interaction.response.send_message(f"❗ You already have a ticket: {ch.mention}", ephemeral=True)
            return
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True)
    }
    name = f"ticket-{ticket_types[cid]}-{user.name}".lower().replace(" ", "-")
    channel = await guild.create_text_channel(name=name, category=category, overwrites=overwrites, topic=f"Ticket by {user.id}")
    await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)
    await channel.send(embed=discord.Embed(
        title=f"🎫 Ticket - {ticket_types[cid].title()}",
        description=f"{user.mention}, thanks for contacting support!\nType `!close` to close this ticket.",
        color=discord.Color.green()
    ))

@bot.command(name="close")
async def close_ticket(ctx):
    if not ctx.channel.topic or "Ticket by" not in ctx.channel.topic:
        await ctx.send("❌ This is not a ticket channel.")
        return
    await ctx.send("🔒 Closing ticket in 5 seconds...")
    await asyncio.sleep(5)
    await ctx.channel.delete()

@bot.command(name="chat")
async def chat_command(ctx, *, message: str):
    if RateLimiter.is_rate_limited(ctx.author.id):
        await ctx.send("⏰ You're sending messages too fast.")
        return
    async with ctx.typing():
        reply = await AIResponseGenerator.generate_response(message, ctx.author.display_name)
        await ctx.send(reply)

def main():
    try:
        logger.info("Starting bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
