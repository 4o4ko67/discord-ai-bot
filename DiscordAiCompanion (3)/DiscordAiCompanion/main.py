#!/usr/bin/env python3
"""
Lightweight Discord AI Bot
A minimal Discord bot with AI responses using Google Gemini, optimized for low storage usage.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
MAX_MESSAGE_LENGTH = 2000  # Discord's message limit
RATE_LIMIT_REQUESTS = 10  # Max requests per user per minute
RATE_LIMIT_WINDOW = 60  # Time window in seconds

# Validate required environment variables
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN environment variable is required")
    exit(1)

if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable is required")
    exit(1)

# Initialize Gemini client
# Note that the newest Gemini model series is "gemini-2.5-flash" or "gemini-2.5-pro"
# do not change this unless explicitly requested by the user
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Initialize bot (remove default help command to use custom one)
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

# Rate limiting storage (in-memory to minimize storage usage)
user_rate_limits: Dict[int, list] = {}

# Counting game storage (in-memory to minimize storage usage)
counting_data: Dict[int, Dict] = {}  # guild_id -> {current_number, last_user_id, channel_id}

class RateLimiter:
    """Simple in-memory rate limiter to prevent API abuse"""
    
    @staticmethod
    def is_rate_limited(user_id: int) -> bool:
        """Check if user is rate limited"""
        now = datetime.now()
        
        # Clean up old entries
        if user_id in user_rate_limits:
            user_rate_limits[user_id] = [
                timestamp for timestamp in user_rate_limits[user_id]
                if now - timestamp < timedelta(seconds=RATE_LIMIT_WINDOW)
            ]
        
        # Check rate limit
        user_requests = user_rate_limits.get(user_id, [])
        if len(user_requests) >= RATE_LIMIT_REQUESTS:
            return True
        
        # Add current request
        if user_id not in user_rate_limits:
            user_rate_limits[user_id] = []
        user_rate_limits[user_id].append(now)
        
        return False

class AIResponseGenerator:
    """Handles AI response generation with Google Gemini"""
    
    @staticmethod
    async def generate_response(message_content: str, user_name: str) -> str:
        """Generate AI response using Google Gemini"""
        try:
            # Create a conversational prompt
            system_prompt = (
                "You are a helpful AI assistant in a Discord chat. "
                "Respond naturally and conversationally. "
                "Keep responses concise but informative. "
                "Be friendly and engaging."
            )
            
            user_prompt = f"{user_name} says: {message_content}"
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Generate response using Google Gemini
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            
            ai_response = response.text.strip() if response.text else "Sorry, I couldn't generate a response."
            
            # Ensure response doesn't exceed Discord's message limit
            if len(ai_response) > MAX_MESSAGE_LENGTH:
                ai_response = ai_response[:MAX_MESSAGE_LENGTH-3] + "..."
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "Sorry, I'm having trouble responding right now. Please try again later."

async def handle_counting_message(message):
    """Handle counting game when someone types just a number"""
    try:
        number = int(message.content.strip())
        guild_id = message.guild.id if message.guild else 0
        
        # Initialize counting game if not exists
        if guild_id not in counting_data:
            if number == 1:
                counting_data[guild_id] = {
                    'current_number': 1,
                    'last_user_id': message.author.id,
                    'channel_id': message.channel.id
                }
                await message.add_reaction("✅")
                await message.reply(f"🎉 **Counting Game Started!** {message.author.mention} started with **1**\nNext person should type **2**")
                return
            else:
                await message.add_reaction("❌")
                await message.reply("❌ Start counting from **1** to begin the game!")
                return
        
        current_data = counting_data[guild_id]
        expected_number = current_data['current_number'] + 1
        
        # Check if it's the same user trying to count twice in a row
        if current_data['last_user_id'] == message.author.id:
            await message.add_reaction("❌")
            await message.reply(f"❌ {message.author.mention} You can't count twice in a row! Let someone else continue.")
            return
        
        # Check if the number is correct
        if number != expected_number:
            await message.add_reaction("❌")
            await message.reply(f"❌ Wrong number! Expected **{expected_number}**, but got **{number}**.\n💥 **Game Over!** Counting restarted. Type **1** to start over.")
            # Reset counting
            counting_data[guild_id] = {
                'current_number': 0,
                'last_user_id': 0,
                'channel_id': message.channel.id
            }
            return
        
        # Correct number! Update the count
        counting_data[guild_id]['current_number'] = number
        counting_data[guild_id]['last_user_id'] = message.author.id
        
        # Add reaction and send response based on milestone
        await message.add_reaction("✅")
        
        if number % 100 == 0:
            await message.reply(f"🎊 **AMAZING!** {message.author.mention} reached **{number}**! 🎊\nNext: **{number + 1}**")
        elif number % 50 == 0:
            await message.reply(f"🌟 **Fantastic!** {message.author.mention} counted **{number}**! 🌟\nNext: **{number + 1}**")
        elif number % 25 == 0:
            await message.reply(f"⭐ **Great job!** {message.author.mention} counted **{number}**!\nNext: **{number + 1}**")
        elif number % 10 == 0:
            await message.reply(f"✨ {message.author.mention} counted **{number}**!\nNext: **{number + 1}**")
        else:
            # For regular numbers, just react without reply to avoid spam
            if number <= 5:  # Give encouragement for first few numbers
                await message.reply(f"✅ {message.author.mention} counted **{number}**! Next: **{number + 1}**")
            
    except ValueError:
        # Not a valid number, ignore
        pass

@bot.event
async def on_ready():
    """Bot startup event"""
    logger.info(f"{bot.user} has connected to Discord!")
    logger.info(f"Bot is in {len(bot.guilds)} guilds")
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="your messages | Type a message to chat!"
        )
    )

@bot.event
async def on_message(message):
    """Handle incoming messages"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from other bots
    if message.author.bot:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Check for counting game (simple number without command)
    if message.content.strip().isdigit():
        await handle_counting_message(message)
        return
    
    # Check if bot is mentioned or message is a DM
    bot_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    # Only respond if mentioned or in DM
    if not (bot_mentioned or is_dm):
        return
    
    # Rate limiting check
    if RateLimiter.is_rate_limited(message.author.id):
        await message.reply(
            "⏰ You're sending messages too quickly! Please wait a moment before trying again.",
            mention_author=False
        )
        return
    
    # Show typing indicator
    async with message.channel.typing():
        try:
            # Clean message content (remove bot mention)
            clean_content = message.content
            if bot_mentioned:
                clean_content = clean_content.replace(f"<@{bot.user.id}>", "").strip()
            
            # Skip if message is empty after cleaning
            if not clean_content:
                await message.reply("Hi! What would you like to talk about?", mention_author=False)
                return
            
            # Generate AI response
            response = await AIResponseGenerator.generate_response(
                clean_content, 
                message.author.display_name
            )
            
            # Send response
            await message.reply(response, mention_author=False)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await message.reply(
                "Sorry, I encountered an error while processing your message. Please try again.",
                mention_author=False
            )

@bot.command(name="help")
async def help_command(ctx):
    """Show help information"""
    embed = discord.Embed(
        title="🤖 AI Discord Bot Help",
        description="I'm an AI assistant that can chat with you!",
        color=0x00ff00
    )
    
    embed.add_field(
        name="💬 How to Chat",
        value="• Mention me in a message: `@bot your message`\n• Send me a direct message\n• Use commands with `!`",
        inline=False
    )
    
    embed.add_field(
        name="🔧 Commands",
        value="`!help` - Show this help message\n`!ping` - Check bot latency\n`!info` - Bot information\n`!chat [message]` - Chat with AI using command\n`!count [number]` - Start or continue counting game\n`!reset_count` - Reset counting game",
        inline=False
    )
    
    embed.add_field(
        name="🔢 Counting Game",
        value="• Type **1** to start counting\n• Next person types **2**, then **3**, etc.\n• Same person can't count twice in a row\n• Wrong number resets the game",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Rate Limits",
        value=f"Maximum {RATE_LIMIT_REQUESTS} requests per minute per user",
        inline=False
    )
    
    embed.set_footer(text="Developed by georgi_4230")
    
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

@bot.command(name="chat")
async def chat_command(ctx, *, message: str = None):
    """Chat with the AI using a command"""
    if not message:
        await ctx.send("❌ Please provide a message to chat with the AI. Example: `!chat Hello there!`")
        return
    
    # Rate limiting check
    if RateLimiter.is_rate_limited(ctx.author.id):
        await ctx.send(
            "⏰ You're sending messages too quickly! Please wait a moment before trying again."
        )
        return
    
    # Show typing indicator
    async with ctx.typing():
        try:
            # Generate AI response
            response = await AIResponseGenerator.generate_response(
                message, 
                ctx.author.display_name
            )
            
            # Send response
            await ctx.send(response)
            
        except Exception as e:
            logger.error(f"Error handling chat command: {e}")
            await ctx.send(
                "Sorry, I encountered an error while processing your message. Please try again."
            )

@bot.command(name="count")
async def count_command(ctx, number: int = None):
    """Start or continue counting game"""
    guild_id = ctx.guild.id if ctx.guild else 0
    
    if number is None:
        # Show current counting status
        if guild_id not in counting_data:
            await ctx.send("🔢 **Counting Game**\nNo counting game started yet! Use `!count 1` to start counting from 1.")
            return
        
        current = counting_data[guild_id]['current_number']
        await ctx.send(f"🔢 **Current Count:** {current}\nNext number should be: **{current + 1}**")
        return
    
    # Initialize counting game if not exists
    if guild_id not in counting_data:
        if number == 1:
            counting_data[guild_id] = {
                'current_number': 1,
                'last_user_id': ctx.author.id,
                'channel_id': ctx.channel.id
            }
            await ctx.send(f"🎉 **Counting Game Started!** {ctx.author.mention} started with **1**\nNext person should type `!count 2`")
            return
        else:
            await ctx.send("❌ Start counting from 1! Use `!count 1` to begin.")
            return
    
    current_data = counting_data[guild_id]
    expected_number = current_data['current_number'] + 1
    
    # Check if it's the same user trying to count twice in a row
    if current_data['last_user_id'] == ctx.author.id:
        await ctx.send(f"❌ {ctx.author.mention} You can't count twice in a row! Let someone else continue.")
        return
    
    # Check if the number is correct
    if number != expected_number:
        await ctx.send(f"❌ Wrong number! Expected **{expected_number}**, but got **{number}**. \nCounting restarted from 1. Use `!count 1` to start over.")
        # Reset counting
        counting_data[guild_id] = {
            'current_number': 0,
            'last_user_id': 0,
            'channel_id': ctx.channel.id
        }
        return
    
    # Correct number! Update the count
    counting_data[guild_id]['current_number'] = number
    counting_data[guild_id]['last_user_id'] = ctx.author.id
    
    # Special milestones
    if number % 100 == 0:
        await ctx.send(f"🎊 **MILESTONE!** {ctx.author.mention} reached **{number}**! 🎊\nNext: **{number + 1}**")
    elif number % 50 == 0:
        await ctx.send(f"🌟 **Great job!** {ctx.author.mention} counted **{number}**! 🌟\nNext: **{number + 1}**")
    elif number % 10 == 0:
        await ctx.send(f"✨ {ctx.author.mention} counted **{number}**! ✨\nNext: **{number + 1}**")
    else:
        await ctx.send(f"✅ {ctx.author.mention} counted **{number}**!\nNext: **{number + 1}**")

@bot.command(name="reset_count")
async def reset_count_command(ctx):
    """Reset the counting game"""
    guild_id = ctx.guild.id if ctx.guild else 0
    
    if guild_id in counting_data:
        del counting_data[guild_id]
        await ctx.send("🔄 **Counting game reset!** Use `!count 1` to start over.")
    else:
        await ctx.send("❌ No counting game to reset.")

@bot.command(name="info")
async def info_command(ctx):
    """Show bot information"""
    embed = discord.Embed(
        title="🤖 Bot Information",
        color=0x0099ff
    )
    
    embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="AI Model", value="Gemini 2.5 Flash", inline=True)
    embed.add_field(name="Version", value="1.0.0", inline=True)
    embed.add_field(name="Lightweight", value="✅ Optimized", inline=True)
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while processing the command.")

def main():
    """Main function to run the bot"""
    try:
        logger.info("Starting AI Discord Bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    main()
