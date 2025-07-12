# Lightweight Discord AI Bot

A minimal Discord bot with ChatGPT-like responses, optimized for low storage usage.

## Features

- 🤖 AI-powered responses using OpenAI's GPT-4o
- 💬 Responds to mentions and direct messages
- ⚡ Built-in rate limiting to prevent API abuse
- 🎯 Minimal storage footprint
- 🔧 Simple command system
- 📊 Basic bot information and help commands

## Quick Setup

1. **Install Dependencies**
   ```bash
   pip install discord.py openai python-dotenv
   ```

2. **Create Environment File**
   ```bash
   cp .env.example .env
   ```

3. **Configure API Keys**
   Edit `.env` file and add your tokens:
   - `DISCORD_TOKEN`: Get from [Discord Developer Portal](https://discord.com/developers/applications)
   - `OPENAI_API_KEY`: Get from [OpenAI Platform](https://platform.openai.com/api-keys)

4. **Run the Bot**
   ```bash
   python main.py
   ```

## Discord Bot Setup

### 1. Create Discord Application
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give your bot a name
4. Go to "Bot" section
5. Click "Add Bot"
6. Copy the bot token to your `.env` file

### 2. Bot Permissions
Your bot needs these permissions:
- Send Messages
- Read Message History
- Use Slash Commands
- Embed Links
- Mention Everyone (optional)

### 3. Invite Bot to Server
1. Go to "OAuth2" > "URL Generator"
2. Select "bot" scope
3. Select required permissions
4. Copy the generated URL and open it to invite the bot

## Usage

### Chat with the Bot
- **Mention the bot**: `@YourBot Hello there!`
- **Direct message**: Send a DM to the bot
- **Commands**: Use `!help` to see available commands

### Commands
- `!help` - Show help information
- `!ping` - Check bot latency
- `!info` - Show bot information

## Storage Optimization

This bot is designed to minimize storage usage:
- **No persistent data storage** - conversations are not saved
- **Minimal file structure** - only essential files
- **In-memory rate limiting** - no database required
- **Single file deployment** - everything in one main.py file
- **No unnecessary dependencies** - only core libraries

## Rate Limiting

- Maximum 10 requests per user per minute
- Prevents API abuse and reduces costs
- Automatic cleanup of old rate limit data

## Error Handling

- Comprehensive error handling for API failures
- User-friendly error messages
- Automatic retry logic where appropriate
- Logging for debugging

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `BOT_PREFIX` | Command prefix | `!` |

## Security Notes

- Never share your API keys
- Use environment variables for sensitive data
- Keep your `.env` file out of version control
- Regularly rotate your API keys

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if bot has proper permissions
   - Verify API keys are correct
   - Check bot is online in Discord

2. **Rate limit errors**
   - Wait a minute before trying again
   - Check OpenAI API usage limits

3. **Permission errors**
   - Ensure bot has "Send Messages" permission
   - Check channel-specific permissions

### Support

If you encounter issues:
1. Check the console logs for error messages
2. Verify all environment variables are set correctly
3. Ensure your API keys are valid and have sufficient credits

## License

This project is open source and available under the MIT License.
