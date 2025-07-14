# Render Deployment Setup

## Files to Upload to GitHub:
1. **main.py** (your bot code)
2. **requirements.txt** with this content:
```
discord.py==2.4.0
google-genai==0.8.0
python-dotenv==1.0.0
```

## Render Configuration:
1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `python main.py`

## Environment Variables in Render:
- `DISCORD_TOKEN`: Your Discord bot token
- `GEMINI_API_KEY`: Your Gemini API key  
- `BOT_PREFIX`: `!`

## Steps:
1. Upload files to GitHub repository
2. Connect GitHub repo to Render
3. Add environment variables in Render
4. Deploy

Your bot will then run 24/7 on Render's free tier.