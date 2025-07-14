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

    # Process commands
    await bot.process_commands(message)

    # If it's a command, stop further handling
    if message.content.startswith(BOT_PREFIX):
        return

    # Counting game (if message is a number)
    if message.content.strip().isdigit():
        await handle_counting_message(message)
        return

    # If mentioned or DM, handle AI response
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
