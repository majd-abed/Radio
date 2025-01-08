import os
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
import json
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

class GeniusClient:
    def __init__(self, access_token: str):
        self.session = requests.Session()
        self.session.headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }

    def search_song(self, query: str):
        try:
            response = self.session.get(
                "https://api.genius.com/search",
                params={'q': query}
            )
            response.raise_for_status()
            return response.json()['response']['hits'][0]['result']
        except Exception as e:
            print(f"Error searching: {e}")
            return None

    def get_lyrics(self, url: str):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try JSON-LD first
            json_data = soup.find('script', type='application/ld+json')
            if json_data:
                data = json.loads(json_data.string)
                if 'lyrics' in data:
                    return data['lyrics'].strip()
            
            # Fallback to HTML parsing
            lyrics_divs = soup.find_all('div', attrs={'data-lyrics-container': 'true'})
            if lyrics_divs:
                lyrics = []
                for div in lyrics_divs:
                    for script in div(['script', 'style']):
                        script.decompose()
                    text = div.get_text(separator='\n').strip()
                    if text:
                        lyrics.append(text)
                return '\n'.join(lyrics)
            
            return None
            
        except Exception as e:
            print(f"Error extracting lyrics: {e}")
            return None

# Initialize Genius client
genius_client = GeniusClient("V3LW6Fa99KPiIBUyN_Oa5m8w-IPLbLHEetZw4XUX7KW6f0v-YsJJHoDAJ3J22Ztf")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_message = """
Welcome to Radio X Lyrics fetcher! 🎵

Just send me the name of any song, and I'll fetch the lyrics for you!

Example:
Toxic Britney Spears
"""
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = """
Just send me the name of any song, and I'll fetch the lyrics for you!

Example:
Toxic Britney Spears
"""
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages and fetch lyrics."""
    query = update.message.text
    
    # Ignore commands
    if query.startswith('/'):
        return

    # Search for the song
    song = genius_client.search_song(query)
    if not song:
        await update.message.reply_text("❌ Sorry, couldn't find that song.")
        return

    # Send song info
    await update.message.reply_text(
        f"✨ Found: {song['title']} by {song['primary_artist']['name']}\n"
        f"🔍 Fetching lyrics..."
    )

    # Get and send lyrics
    lyrics = genius_client.get_lyrics(song['url'])
    if lyrics:
        # Format the header
        header = f"[ {song['title']} - {song['primary_artist']['name']} ]\n"
        
        # Combine header and lyrics
        formatted_lyrics = header + lyrics
        
        # Split long lyrics into multiple messages if needed
        max_length = 4096  # Telegram's message length limit
        lyrics_parts = [formatted_lyrics[i:i + max_length] for i in range(0, len(formatted_lyrics), max_length)]
        
        for part in lyrics_parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(
            "❌ Sorry, couldn't fetch the lyrics.\n"
            f"You can find them here: {song['url']}"
        )

def main():
    """Start the bot."""
    # Replace with your bot token from BotFather
    TELEGRAM_TOKEN = "7657838266:AAG8Vf6OOXBTehoE5-mWJL8kmaxyN5L33iA"
    
    # Create application and add handlers
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handler for direct song queries
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
