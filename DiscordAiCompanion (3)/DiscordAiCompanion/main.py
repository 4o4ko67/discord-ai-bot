#!/usr/bin/env python3
"""
Lightweight Discord AI Bot with FastAPI server for Render & Localhost
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import discord
from discord.ext import commands
from google import genai
from fastapi import FastAPI
import uvicorn

# ===================== Logging =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===================== Config =====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN environment variable is required")
    exit(1)
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable is required")
    exit(1)

# ===================== Gemini =====================
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ===================== Bot Setup =====================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

user_rate_limits: Dict[int, list] = {}
counting_data: Dict[int, Dict] = {}

class RateLimiter:
    @staticmethod
    def is_rate_limited(user_id: int) -> bool:
        now = datetime.now()
        if user_id in user_rate_limits:
            user_rate_limits[user_id] = [
                ts for ts in user_rate_limits[user_id]
                if now - ts < timedelta(seconds=RATE_LIMIT_WINDOW)
            ]
        reqs = user_rate_limits.get(user_id, [])
        if len(reqs) >= RATE_LIMIT_REQUESTS:
            return True
        user_rate_limits.setdefault(user_id, []).append(now)
        return False

class AIResponseGenerator:
    @staticmethod
    async def generate_response(msg: str, user_name: str) -> str:
        try:
            prompt = (
                "You are a helpful AI assistant in a Discord chat. "
                "Respond naturally and conversationally. "
                "Keep responses concise but informative. "
                "Be friendly and engaging.\n\n"
                f"{user_name} says: {msg}"
            )
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = response.text.strip() if response.text else "Sorry, no response."
            return text[:MAX_MESSAGE_LENGTH] if len(text) <= MAX_MESSAGE_LENGTH else text[:MAX_MESSAGE_LENGTH-3]+"..."
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "Sorry, I couldn't process that."

async def handle_counting_message(message):
    try:
        number = int(message.content.strip())
        guild_id = message.guild.id if message.guild else 0

        if guild_id not in counting_data:
            if number == 1:
                counting_data[guild_id] = {
                    'current_number': 1,
                    'last_user_id': message.author.id,
                    'channel_id': message.channel.id
                }
                await message.add_reaction("✅")
                await message.reply(f"🎉 Counting started by {message.author.mention} with **1**. Next: **2**")
                return
            else:
                await message.add_reaction("❌")
                await message.reply("❌ Start from **1** to begin counting!")
                return

        current = counting_data[guild_id]
        expected = current['current_number'] + 1

        if current['last_user_id'] == message.author.id:
            await message.add_reaction("❌")
            await message.reply("❌ You can't count twice in a row!")
            return

        if number != expected:
            await message.add_reaction("❌")
            await message.reply(f"❌ Wrong! Expected **{expected}**. Restart from **1**.")
            counting_data[guild_id] = {
                'current_number': 0,
                'last_user_id': 0,
                'channel_id': message.channel.id
            }
            return

        counting_data[guild_id]['current_number'] = number
        counting_data[guild_id]['last_user_id'] = message.author.id

        await message.add_reaction("✅")

        if number % 100 == 0:
            await message.reply(f"🎉 **{number}!** Huge milestone!")
        elif number % 50 == 0:
            await message.reply(f"🌟 **{number}!** Keep it up!")
        elif number % 10 == 0:
            await message.reply(f"✨ {number} reached!")
        elif number <= 5:
            await message.reply(f"✅ {number} done! Next: {number+1}")
    except ValueError:
        pass

# ===================== Events =====================
@bot.event
async def on_ready():
    logger.info(f"{bot.user} is online!")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your messages | @ me!"
        )
    )

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
    await bot.process_commands(message)

    if message.content.strip().isdigit():
        await handle_counting_message(message)
        return

    bot_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    if not (bot_mentioned or is_dm):
        return

    if RateLimiter.is_rate_limited(message.author.id):
        await message.reply("⏰ Too fast! Slow down.", mention_author=False)
        return

    async with message.channel.typing():
        content = message.content.replace(f"<@{bot.user.id}>", "").strip() if bot_mentioned else message.content
        if not content:
            await message.reply("Hi! What would you like to talk about?", mention_author=False)
            return
        response = await AIResponseGenerator.generate_response(content, message.author.display_name)
        await message.reply(response, mention_author=False)

# ===================== Commands =====================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 Help",
        description="How to use this bot",
        color=0x00ff00
    )
    embed.add_field(name="💬 Chat", value="Mention me or DM me.", inline=False)
    embed.add_field(name="🔧 Commands", value="!help, !ping, !info, !count, !reset_count, !chat", inline=False)
    embed.add_field(name="🔢 Counting", value="Type **1** to start counting.", inline=False)
    embed.add_field(name="⚡ Rate Limits", value=f"{RATE_LIMIT_REQUESTS} requests/min per user.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! {latency}ms")

@bot.command(name="chat")
async def chat_command(ctx, *, message: str = None):
    if not message:
        await ctx.send("❌ Please include a message. Example: `!chat Hello`")
        return
    if RateLimiter.is_rate_limited(ctx.author.id):
        await ctx.send("⏰ Slow down please.")
        return
    async with ctx.typing():
        response = await AIResponseGenerator.generate_response(message, ctx.author.display_name)
        await ctx.send(response)

@bot.command(name="count")
async def count_command(ctx, number: int = None):
    guild_id = ctx.guild.id if ctx.guild else 0
    if number is None:
        if guild_id not in counting_data:
            await ctx.send("No counting yet. Use `!count 1` to start.")
        else:
            curr = counting_data[guild_id]['current_number']
            await ctx.send(f"Current: **{curr}**, next: **{curr+1}**")
        return

    if guild_id not in counting_data:
        if number == 1:
            counting_data[guild_id] = {'current_number': 1, 'last_user_id': ctx.author.id, 'channel_id': ctx.channel.id}
            await ctx.send(f"Started by {ctx.author.mention} with **1**. Next: `!count 2`")
        else:
            await ctx.send("Start from 1 please!")
        return

    curr = counting_data[guild_id]
    expected = curr['current_number'] + 1

    if curr['last_user_id'] == ctx.author.id:
        await ctx.send("❌ You can't count twice in a row.")
        return

    if number != expected:
        await ctx.send(f"❌ Wrong! Expected **{expected}**. Restart from `!count 1`.")
        counting_data[guild_id] = {'current_number': 0, 'last_user_id': 0, 'channel_id': ctx.channel.id}
        return

    counting_data[guild_id]['current_number'] = number
    counting_data[guild_id]['last_user_id'] = ctx.author.id
    await ctx.send(f"✅ {number} done! Next: **{number+1}**")

@bot.command(name="reset_count")
async def reset_count_command(ctx):
    guild_id = ctx.guild.id if ctx.guild else 0
    if guild_id in counting_data:
        del counting_data[guild_id]
        await ctx.send("🔄 Counting reset.")
    else:
        await ctx.send("No counting to reset.")

@bot.command(name="info")
async def info_command(ctx):
    embed = discord.Embed(
        title="Bot Info",
        color=0x0099ff
    )
    embed.add_field(name="Guilds", value=len(bot.guilds))
    embed.add_field(name="Users", value=len(bot.users))
    embed.add_field(name="Latency", value=f"{round(bot.latency*1000)}ms")
    embed.add_field(name="Model", value="Gemini 2.5 Flash")
    embed.add_field(name="Version", value="1.0.0")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `!help`.")
    else:
        logger.error(error)
        await ctx.send("❌ Error processing command.")

# ===================== FastAPI =====================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot is running", "guilds": len(bot.guilds)}

async def run():
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(DISCORD_TOKEN))
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run())#!/usr/bin/env python3
"""
Lightweight Discord AI Bot with FastAPI server for Render & Localhost
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import discord
from discord.ext import commands
from google import genai
from fastapi import FastAPI
import uvicorn

# ===================== Logging =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===================== Config =====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN environment variable is required")
    exit(1)
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable is required")
    exit(1)

# ===================== Gemini =====================
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ===================== Bot Setup =====================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

user_rate_limits: Dict[int, list] = {}
counting_data: Dict[int, Dict] = {}

class RateLimiter:
    @staticmethod
    def is_rate_limited(user_id: int) -> bool:
        now = datetime.now()
        if user_id in user_rate_limits:
            user_rate_limits[user_id] = [
                ts for ts in user_rate_limits[user_id]
                if now - ts < timedelta(seconds=RATE_LIMIT_WINDOW)
            ]
        reqs = user_rate_limits.get(user_id, [])
        if len(reqs) >= RATE_LIMIT_REQUESTS:
            return True
        user_rate_limits.setdefault(user_id, []).append(now)
        return False

class AIResponseGenerator:
    @staticmethod
    async def generate_response(msg: str, user_name: str) -> str:
        try:
            prompt = (
                "You are a helpful AI assistant in a Discord chat. "
                "Respond naturally and conversationally. "
                "Keep responses concise but informative. "
                "Be friendly and engaging.\n\n"
                f"{user_name} says: {msg}"
            )
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = response.text.strip() if response.text else "Sorry, no response."
            return text[:MAX_MESSAGE_LENGTH] if len(text) <= MAX_MESSAGE_LENGTH else text[:MAX_MESSAGE_LENGTH-3]+"..."
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "Sorry, I couldn't process that."

async def handle_counting_message(message):
    try:
        number = int(message.content.strip())
        guild_id = message.guild.id if message.guild else 0

        if guild_id not in counting_data:
            if number == 1:
                counting_data[guild_id] = {
                    'current_number': 1,
                    'last_user_id': message.author.id,
                    'channel_id': message.channel.id
                }
                await message.add_reaction("✅")
                await message.reply(f"🎉 Counting started by {message.author.mention} with **1**. Next: **2**")
                return
            else:
                await message.add_reaction("❌")
                await message.reply("❌ Start from **1** to begin counting!")
                return

        current = counting_data[guild_id]
        expected = current['current_number'] + 1

        if current['last_user_id'] == message.author.id:
            await message.add_reaction("❌")
            await message.reply("❌ You can't count twice in a row!")
            return

        if number != expected:
            await message.add_reaction("❌")
            await message.reply(f"❌ Wrong! Expected **{expected}**. Restart from **1**.")
            counting_data[guild_id] = {
                'current_number': 0,
                'last_user_id': 0,
                'channel_id': message.channel.id
            }
            return

        counting_data[guild_id]['current_number'] = number
        counting_data[guild_id]['last_user_id'] = message.author.id

        await message.add_reaction("✅")

        if number % 100 == 0:
            await message.reply(f"🎉 **{number}!** Huge milestone!")
        elif number % 50 == 0:
            await message.reply(f"🌟 **{number}!** Keep it up!")
        elif number % 10 == 0:
            await message.reply(f"✨ {number} reached!")
        elif number <= 5:
            await message.reply(f"✅ {number} done! Next: {number+1}")
    except ValueError:
        pass

# ===================== Events =====================
@bot.event
async def on_ready():
    logger.info(f"{bot.user} is online!")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your messages | @ me!"
        )
    )

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
    await bot.process_commands(message)

    if message.content.strip().isdigit():
        await handle_counting_message(message)
        return

    bot_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    if not (bot_mentioned or is_dm):
        return

    if RateLimiter.is_rate_limited(message.author.id):
        await message.reply("⏰ Too fast! Slow down.", mention_author=False)
        return

    async with message.channel.typing():
        content = message.content.replace(f"<@{bot.user.id}>", "").strip() if bot_mentioned else message.content
        if not content:
            await message.reply("Hi! What would you like to talk about?", mention_author=False)
            return
        response = await AIResponseGenerator.generate_response(content, message.author.display_name)
        await message.reply(response, mention_author=False)

# ===================== Commands =====================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 Help",
        description="How to use this bot",
        color=0x00ff00
    )
    embed.add_field(name="💬 Chat", value="Mention me or DM me.", inline=False)
    embed.add_field(name="🔧 Commands", value="!help, !ping, !info, !count, !reset_count, !chat", inline=False)
    embed.add_field(name="🔢 Counting", value="Type **1** to start counting.", inline=False)
    embed.add_field(name="⚡ Rate Limits", value=f"{RATE_LIMIT_REQUESTS} requests/min per user.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! {latency}ms")

@bot.command(name="chat")
async def chat_command(ctx, *, message: str = None):
    if not message:
        await ctx.send("❌ Please include a message. Example: `!chat Hello`")
        return
    if RateLimiter.is_rate_limited(ctx.author.id):
        await ctx.send("⏰ Slow down please.")
        return
    async with ctx.typing():
        response = await AIResponseGenerator.generate_response(message, ctx.author.display_name)
        await ctx.send(response)

@bot.command(name="count")
async def count_command(ctx, number: int = None):
    guild_id = ctx.guild.id if ctx.guild else 0
    if number is None:
        if guild_id not in counting_data:
            await ctx.send("No counting yet. Use `!count 1` to start.")
        else:
            curr = counting_data[guild_id]['current_number']
            await ctx.send(f"Current: **{curr}**, next: **{curr+1}**")
        return

    if guild_id not in counting_data:
        if number == 1:
            counting_data[guild_id] = {'current_number': 1, 'last_user_id': ctx.author.id, 'channel_id': ctx.channel.id}
            await ctx.send(f"Started by {ctx.author.mention} with **1**. Next: `!count 2`")
        else:
            await ctx.send("Start from 1 please!")
        return

    curr = counting_data[guild_id]
    expected = curr['current_number'] + 1

    if curr['last_user_id'] == ctx.author.id:
        await ctx.send("❌ You can't count twice in a row.")
        return

    if number != expected:
        await ctx.send(f"❌ Wrong! Expected **{expected}**. Restart from `!count 1`.")
        counting_data[guild_id] = {'current_number': 0, 'last_user_id': 0, 'channel_id': ctx.channel.id}
        return

    counting_data[guild_id]['current_number'] = number
    counting_data[guild_id]['last_user_id'] = ctx.author.id
    await ctx.send(f"✅ {number} done! Next: **{number+1}**")

@bot.command(name="reset_count")
async def reset_count_command(ctx):
    guild_id = ctx.guild.id if ctx.guild else 0
    if guild_id in counting_data:
        del counting_data[guild_id]
        await ctx.send("🔄 Counting reset.")
    else:
        await ctx.send("No counting to reset.")

@bot.command(name="info")
async def info_command(ctx):
    embed = discord.Embed(
        title="Bot Info",
        color=0x0099ff
    )
    embed.add_field(name="Guilds", value=len(bot.guilds))
    embed.add_field(name="Users", value=len(bot.users))
    embed.add_field(name="Latency", value=f"{round(bot.latency*1000)}ms")
    embed.add_field(name="Model", value="Gemini 2.5 Flash")
    embed.add_field(name="Version", value="1.0.0")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `!help`.")
    else:
        logger.error(error)
        await ctx.send("❌ Error processing command.")

# ===================== FastAPI =====================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot is running", "guilds": len(bot.guilds)}

async def run():
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(DISCORD_TOKEN))
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run())#!/usr/bin/env python3
"""
Lightweight Discord AI Bot with FastAPI server for Render & Localhost
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import discord
from discord.ext import commands
from google import genai
from fastapi import FastAPI
import uvicorn

# ===================== Logging =====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===================== Config =====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW = 60

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN environment variable is required")
    exit(1)
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable is required")
    exit(1)

# ===================== Gemini =====================
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ===================== Bot Setup =====================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

user_rate_limits: Dict[int, list] = {}
counting_data: Dict[int, Dict] = {}

class RateLimiter:
    @staticmethod
    def is_rate_limited(user_id: int) -> bool:
        now = datetime.now()
        if user_id in user_rate_limits:
            user_rate_limits[user_id] = [
                ts for ts in user_rate_limits[user_id]
                if now - ts < timedelta(seconds=RATE_LIMIT_WINDOW)
            ]
        reqs = user_rate_limits.get(user_id, [])
        if len(reqs) >= RATE_LIMIT_REQUESTS:
            return True
        user_rate_limits.setdefault(user_id, []).append(now)
        return False

class AIResponseGenerator:
    @staticmethod
    async def generate_response(msg: str, user_name: str) -> str:
        try:
            prompt = (
                "You are a helpful AI assistant in a Discord chat. "
                "Respond naturally and conversationally. "
                "Keep responses concise but informative. "
                "Be friendly and engaging.\n\n"
                f"{user_name} says: {msg}"
            )
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = response.text.strip() if response.text else "Sorry, no response."
            return text[:MAX_MESSAGE_LENGTH] if len(text) <= MAX_MESSAGE_LENGTH else text[:MAX_MESSAGE_LENGTH-3]+"..."
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return "Sorry, I couldn't process that."

async def handle_counting_message(message):
    try:
        number = int(message.content.strip())
        guild_id = message.guild.id if message.guild else 0

        if guild_id not in counting_data:
            if number == 1:
                counting_data[guild_id] = {
                    'current_number': 1,
                    'last_user_id': message.author.id,
                    'channel_id': message.channel.id
                }
                await message.add_reaction("✅")
                await message.reply(f"🎉 Counting started by {message.author.mention} with **1**. Next: **2**")
                return
            else:
                await message.add_reaction("❌")
                await message.reply("❌ Start from **1** to begin counting!")
                return

        current = counting_data[guild_id]
        expected = current['current_number'] + 1

        if current['last_user_id'] == message.author.id:
            await message.add_reaction("❌")
            await message.reply("❌ You can't count twice in a row!")
            return

        if number != expected:
            await message.add_reaction("❌")
            await message.reply(f"❌ Wrong! Expected **{expected}**. Restart from **1**.")
            counting_data[guild_id] = {
                'current_number': 0,
                'last_user_id': 0,
                'channel_id': message.channel.id
            }
            return

        counting_data[guild_id]['current_number'] = number
        counting_data[guild_id]['last_user_id'] = message.author.id

        await message.add_reaction("✅")

        if number % 100 == 0:
            await message.reply(f"🎉 **{number}!** Huge milestone!")
        elif number % 50 == 0:
            await message.reply(f"🌟 **{number}!** Keep it up!")
        elif number % 10 == 0:
            await message.reply(f"✨ {number} reached!")
        elif number <= 5:
            await message.reply(f"✅ {number} done! Next: {number+1}")
    except ValueError:
        pass

# ===================== Events =====================
@bot.event
async def on_ready():
    logger.info(f"{bot.user} is online!")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your messages | @ me!"
        )
    )

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return
    await bot.process_commands(message)

    if message.content.strip().isdigit():
        await handle_counting_message(message)
        return

    bot_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    if not (bot_mentioned or is_dm):
        return

    if RateLimiter.is_rate_limited(message.author.id):
        await message.reply("⏰ Too fast! Slow down.", mention_author=False)
        return

    async with message.channel.typing():
        content = message.content.replace(f"<@{bot.user.id}>", "").strip() if bot_mentioned else message.content
        if not content:
            await message.reply("Hi! What would you like to talk about?", mention_author=False)
            return
        response = await AIResponseGenerator.generate_response(content, message.author.display_name)
        await message.reply(response, mention_author=False)

# ===================== Commands =====================
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="🤖 Help",
        description="How to use this bot",
        color=0x00ff00
    )
    embed.add_field(name="💬 Chat", value="Mention me or DM me.", inline=False)
    embed.add_field(name="🔧 Commands", value="!help, !ping, !info, !count, !reset_count, !chat", inline=False)
    embed.add_field(name="🔢 Counting", value="Type **1** to start counting.", inline=False)
    embed.add_field(name="⚡ Rate Limits", value=f"{RATE_LIMIT_REQUESTS} requests/min per user.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! {latency}ms")

@bot.command(name="chat")
async def chat_command(ctx, *, message: str = None):
    if not message:
        await ctx.send("❌ Please include a message. Example: `!chat Hello`")
        return
    if RateLimiter.is_rate_limited(ctx.author.id):
        await ctx.send("⏰ Slow down please.")
        return
    async with ctx.typing():
        response = await AIResponseGenerator.generate_response(message, ctx.author.display_name)
        await ctx.send(response)

@bot.command(name="count")
async def count_command(ctx, number: int = None):
    guild_id = ctx.guild.id if ctx.guild else 0
    if number is None:
        if guild_id not in counting_data:
            await ctx.send("No counting yet. Use `!count 1` to start.")
        else:
            curr = counting_data[guild_id]['current_number']
            await ctx.send(f"Current: **{curr}**, next: **{curr+1}**")
        return

    if guild_id not in counting_data:
        if number == 1:
            counting_data[guild_id] = {'current_number': 1, 'last_user_id': ctx.author.id, 'channel_id': ctx.channel.id}
            await ctx.send(f"Started by {ctx.author.mention} with **1**. Next: `!count 2`")
        else:
            await ctx.send("Start from 1 please!")
        return

    curr = counting_data[guild_id]
    expected = curr['current_number'] + 1

    if curr['last_user_id'] == ctx.author.id:
        await ctx.send("❌ You can't count twice in a row.")
        return

    if number != expected:
        await ctx.send(f"❌ Wrong! Expected **{expected}**. Restart from `!count 1`.")
        counting_data[guild_id] = {'current_number': 0, 'last_user_id': 0, 'channel_id': ctx.channel.id}
        return

    counting_data[guild_id]['current_number'] = number
    counting_data[guild_id]['last_user_id'] = ctx.author.id
    await ctx.send(f"✅ {number} done! Next: **{number+1}**")

@bot.command(name="reset_count")
async def reset_count_command(ctx):
    guild_id = ctx.guild.id if ctx.guild else 0
    if guild_id in counting_data:
        del counting_data[guild_id]
        await ctx.send("🔄 Counting reset.")
    else:
        await ctx.send("No counting to reset.")

@bot.command(name="info")
async def info_command(ctx):
    embed = discord.Embed(
        title="Bot Info",
        color=0x0099ff
    )
    embed.add_field(name="Guilds", value=len(bot.guilds))
    embed.add_field(name="Users", value=len(bot.users))
    embed.add_field(name="Latency", value=f"{round(bot.latency*1000)}ms")
    embed.add_field(name="Model", value="Gemini 2.5 Flash")
    embed.add_field(name="Version", value="1.0.0")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown command. Use `!help`.")
    else:
        logger.error(error)
        await ctx.send("❌ Error processing command.")

# ===================== FastAPI =====================
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot is running", "guilds": len(bot.guilds)}

async def run():
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(DISCORD_TOKEN))
    port = int(os.getenv("PORT", 8080))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run())
