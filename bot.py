import os
from typing import Optional, Dict
import requests
from bs4 import BeautifulSoup
import json
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GeniusClient:
    def __init__(self, access_token: str):
        self.session = requests.Session()
        self.session.headers = {
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
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
            logger.error(f"Error searching: {e}")
            return None

    def get_lyrics(self, url: str) -> Optional[str]:
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            logger.debug(f"Fetching lyrics from URL: {url}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all divs that contain actual lyrics sections [Verse], [Chorus] etc.
            lyrics_sections = soup.find_all('div', attrs={'data-lyrics-container': 'true'})
            
            if lyrics_sections:
                lyrics = []
                for section in lyrics_sections:
                    # Get text while preserving line breaks
                    section_text = '\n'.join(line.strip() for line in section.stripped_strings)
                    if section_text:  # Only add non-empty sections
                        lyrics.append(section_text)
                
                return '\n'.join(lyrics).strip()
                
            return None
                    
        except Exception as e:
            logger.error(f"Error extracting lyrics: {e}", exc_info=True)
            return None

class LyricsBot:
    def __init__(self, telegram_token: str, genius_token: str):
        self.telegram_token = telegram_token
        self.genius_client = GeniusClient(genius_token)
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        welcome_message = """
Welcome to Radio X Lyrics fetcher! 🎵

Just send me the name of any song, and I'll fetch the lyrics for you!

Example:
Toxic Britney Spears
"""
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        help_text = """
Just send me the name of any song, and I'll fetch the lyrics for you!

Example:
Toxic Britney Spears
"""
        await update.message.reply_text(help_text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages and fetch lyrics."""
        query = update.message.text
        
        # Ignore commands
        if query.startswith('/'):
            return

        try:
            # Search for the song
            song = self.genius_client.search_song(query)
            if not song:
                await update.message.reply_text("❌ Sorry, couldn't find that song.")
                return

            # Send song info with modified format
            await update.message.reply_text(
                f"✨ Found: {song['title']} by {song['primary_artist']['name']}\n"
                f"🔍 Fetching lyrics..."
            )

            # Get and send lyrics
            lyrics = self.genius_client.get_lyrics(song['url'])
            if lyrics:
                # Format the header with new style
                header = f"[ {song['title']} - {song['primary_artist']['name']} ]\n\n"
                
                # Combine header and lyrics
                formatted_lyrics = header + lyrics
                
                # Split long lyrics into multiple messages if needed
                max_length = 4096  # Telegram's message length limit
                lyrics_parts = [formatted_lyrics[i:i + max_length] 
                              for i in range(0, len(formatted_lyrics), max_length)]
                
                for part in lyrics_parts:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(
                    "❌ Sorry, couldn't fetch the lyrics.\n"
                    f"You can find them here: {song['url']}"
                )
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ Sorry, something went wrong while processing your request."
            )

    def run(self):
        """Start the bot."""
        try:
            # Create application and add handlers
            self.application = Application.builder().token(self.telegram_token).build()

            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start))
            self.application.add_handler(CommandHandler("help", self.help_command))
            
            # Add message handler for direct song queries
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )

            # Start the bot
            logger.info("Bot is starting...")
            self.application.run_polling()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)

def main():
    # Your tokens
    TELEGRAM_TOKEN = "7657838266:AAG8Vf6OOXBTehoE5-mWJL8kmaxyN5L33iA"
    GENIUS_TOKEN = "V3LW6Fa99KPiIBUyN_Oa5m8w-IPLbLHEetZw4XUX7KW6f0v-YsJJHoDAJ3J22Ztf"
    
    # Create and run the bot
    bot = LyricsBot(TELEGRAM_TOKEN, GENIUS_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()
