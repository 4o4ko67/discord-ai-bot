# Lightweight Discord AI Bot

## Overview

This is a minimal Discord bot with ChatGPT-like responses, designed for low storage usage. The bot responds to mentions and direct messages using OpenAI's GPT-4o model, includes built-in rate limiting to prevent API abuse, and provides basic bot information and help commands.

## User Preferences

Preferred communication style: Simple, everyday language.
Preferred AI service: Google AI Studio (Gemini) instead of OpenAI for cost-effectiveness.

## System Architecture

### Core Architecture
- **Language**: Python 3
- **Framework**: discord.py for Discord API integration
- **AI Service**: OpenAI GPT-4o for chat responses
- **Configuration**: Environment variables for sensitive data
- **Logging**: Python's built-in logging module

### Design Principles
- Minimal storage footprint
- Simple command system
- Rate limiting for API protection
- Environment-based configuration

## Key Components

### 1. Discord Bot Integration
- **Framework**: discord.py library
- **Intents**: Default intents with message content and guild access
- **Permissions Required**: Send Messages, Read Message History, Use Slash Commands

### 2. Google Gemini Integration
- **Model**: Gemini 2.5 Flash (Google's latest multimodal AI model)
- **Client**: Google GenAI Python library
- **Configuration**: API key managed through environment variables

### 3. Rate Limiting System
- **Limit**: 10 requests per user per minute
- **Window**: 60-second time window
- **Purpose**: Prevent API abuse and manage costs

### 4. Configuration Management
- **Method**: Environment variables via python-dotenv
- **Required Variables**:
  - `DISCORD_TOKEN`: Discord bot token
  - `GEMINI_API_KEY`: Google AI Studio API key
- **Optional Variables**:
  - `BOT_PREFIX`: Command prefix (default: "!")

## Data Flow

### Message Processing Flow
1. Bot receives Discord message (mention or DM)
2. Rate limiting check performed
3. Message content extracted and processed
4. Google Gemini API call made with Gemini 2.5 Flash
5. Response formatted and sent back to Discord
6. Error handling and logging throughout

### Response Handling
- Maximum message length: 2000 characters (Discord limit)
- Automatic message truncation if needed
- Error responses for failed API calls

## External Dependencies

### Required Python Packages
- `discord.py`: Discord API wrapper
- `google-genai`: Google Generative AI client
- `python-dotenv`: Environment variable management

### External Services
- **Discord API**: For bot functionality and message handling
- **Google AI Studio API**: For AI-powered responses using Gemini 2.5 Flash model

### API Requirements
- Discord bot token from Discord Developer Portal
- Google Gemini API key from Google AI Studio

## Deployment Strategy

### Environment Setup
1. Install Python dependencies via pip
2. Create `.env` file from `.env.example`
3. Configure Discord and Google Gemini API keys
4. Run bot with `python main.py`

### Minimal Resource Requirements
- Low storage footprint design
- No database requirements
- Stateless operation (no persistent data storage)
- Memory-efficient rate limiting using in-memory tracking

### Error Handling
- Comprehensive logging for debugging
- Graceful handling of API failures
- Input validation for required environment variables
- Automatic bot shutdown if critical configuration is missing

### Security Considerations
- API keys stored in environment variables
- Rate limiting to prevent abuse
- No sensitive data persistence
- Minimal permission requirements for Discord bot