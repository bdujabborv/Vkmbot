#!/usr/bin/env python3
"""
Telegram Media Downloader Bot
Instagram, YouTube, TikTok va boshqa platformalardan video yuklab oluvchi bot
"""

import os
import asyncio
import logging
import tempfile
import shutil
from datetime import datetime
from urllib.parse import urlparse
import re

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Bot Configuration
BOT_TOKEN='8437960997:AAHsEMgqmAss1aqQcAzpa3DugQLTERA9168'
ADMIN_ID='5922089904'

# File Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
TEMP_DIR = './temp'

# Supported Platforms
SUPPORTED_PLATFORMS = [
    'youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com',
    'facebook.com', 'twitter.com', 'x.com', 'vimeo.com',
    'dailymotion.com', 'twitch.tv'
]

# Bot Messages
MESSAGES = {
    'start': '''🎬 Assalomu alaykum! Men sizga ijtimoiy tarmoqlardan video yuklab beraman.

📱 Qo'llab-quvvatlanadigan platformalar:
• YouTube (youtu.be, youtube.com)
• Instagram
• TikTok
• Facebook
• Twitter/X
• Vimeo
• Twitch
• Dailymotion

🔗 Foydalanish: Video linkini yuboring''',

    'help': '''📚 Bot qanday ishlaydi:

🔗 Video yuklab olish:
1. Video linkini yuboring
2. Sifatni tanlang
3. Yuklashni kuting

💡 Maslahatlar:
• Qisqa videolar tezroq yuklanadi
• Maksimal fayl hajmi: 50MB
• Barcha formatlar qo'llab-quvvatlanadi

❓ Yordam kerakmi? /help''',

    'processing': '⏳ Link tekshirilmoqda...',
    'downloading': '📥 Video yuklanmoqda...',
    'uploading': '📤 Telegram ga yuklanmoqda...',
    'invalid_url': '❌ Noto\'g\'ri link. Qo\'llab-quvvatlanadigan platformadan link yuboring.',
    'download_error': '❌ Yuklashda xatolik. Link tekshiring yoki boshqa video sinab ko\'ring.',
    'file_too_large': '❌ Video hajmi juda katta (max 50MB). Boshqa sifatni tanlang.',
    'success': '✅ Video muvaffaqiyatli yuklandi!',
    'error': '❌ Xatolik yuz berdi. Qaytadan urinib ko\'ring.',
    'unsupported': '❌ Bu platform hozircha qo\'llab-quvvatlanmaydi.',
    'no_video': '❌ Video topilmadi. Link tekshiring.',
    'timeout': '❌ Vaqt tugadi. Qaytadan urinib ko\'ring.'
}

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create temp directory
os.makedirs(TEMP_DIR, exist_ok=True)

class MediaBot:
    def __init__(self):
        self.downloading = set()  # Track active downloads

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        keyboard = [
            [InlineKeyboardButton("📹 Video yuklab olish", callback_data="help_video")],
            [InlineKeyboardButton("📚 Qo'llanma", callback_data="help")],
            [InlineKeyboardButton("ℹ️ Bot haqida", callback_data="about")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(MESSAGES['start'], reply_markup=reply_markup)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        await update.message.reply_text(MESSAGES['help'])

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        if query.data == "help_video":
            text = """📹 Video yuklab olish:

🔗 Quyidagi platformalardan link yuboring:
• YouTube: https://youtu.be/xxxxx
• Instagram: https://instagram.com/p/xxxxx
• TikTok: https://tiktok.com/@user/video/xxxxx
• Facebook, Twitter, Vimeo va boshqalar

⚙️ Sifat tanlovlari:
• 🔥 Eng yuqori sifat (HD/4K)
• ⚡ O'rta sifat (tez yuklanadi)
• 🎵 Faqat audio (MP3)

💡 Video linkini yuboring va sifatni tanlang!"""

        elif query.data == "help":
            text = MESSAGES['help']

        elif query.data == "about":
            text = """ℹ️ Bot haqida:

🤖 Telegram Media Downloader Bot
📅 Versiya: 1.0
⚡ Python + yt-dlp
🆓 To'liq bepul

👨‍💻 Yaratuvchi: @your_username
📞 Yordam: /help

🔒 Xavfsizlik: Barcha fayllar vaqtinchalik saqlanadi"""

        else:
            text = MESSAGES['start']

        keyboard = [[InlineKeyboardButton("◀️ Orqaga", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)

    def is_supported_url(self, url: str) -> bool:
        """Check if URL is from supported platform"""
        try:
            # Clean URL
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            domain = urlparse(url).netloc.lower()
            return any(platform in domain for platform in SUPPORTED_PLATFORMS)
        except:
            return False

    def extract_url_from_text(self, text: str) -> str:
        """Extract URL from text message"""
        # Find URLs in text
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)

        if urls:
            return urls[0]

        # Check if text itself is a URL (without http)
        if any(platform in text.lower() for platform in SUPPORTED_PLATFORMS):
            return text.strip()

        return None

    async def get_video_info(self, url: str) -> dict:
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    'success': True,
                    'title': info.get('title', 'Video')[:100],  # Limit title length
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'formats': len(info.get('formats', [])),
                    'thumbnail': info.get('thumbnail')
                }

        except Exception as e:
            logger.error(f"Info extraction error: {e}")
            return {'success': False, 'error': str(e)}

    async def download_video(self, url: str, quality: str = 'best', user_id: int = None) -> dict:
        """Download video using yt-dlp"""
        try:
            # Prevent multiple downloads from same user
            if user_id in self.downloading:
                return {'success': False, 'error': 'already_downloading'}

            self.downloading.add(user_id)

            # Set format based on quality
            if quality == 'audio':
                format_selector = 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio'
                ext = 'mp3'
            elif quality == 'worst':
                format_selector = 'worst[height<=480]/worst'
                ext = 'mp4'
            else:  # best
                format_selector = 'best[height<=720]/best[ext=mp4]/best'
                ext = 'mp4'

            # Unique filename
            timestamp = int(datetime.now().timestamp())
            filename = f"video_{user_id}_{timestamp}"

            # yt-dlp options
            ydl_opts = {
                'format': format_selector,
                'outtmpl': f'{TEMP_DIR}/{filename}.%(ext)s',
                'max_filesize': MAX_FILE_SIZE,
                'writeinfojson': False,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'ignoreerrors': False,
                'no_warnings': True,
                'extractaudio': quality == 'audio',
                'audioformat': 'mp3' if quality == 'audio' else None,
                'audioquality': '192' if quality == 'audio' else None,
            }

            # Add post-processor for audio
            if quality == 'audio':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download
                ydl.download([url])

                # Find downloaded file
                for file in os.listdir(TEMP_DIR):
                    if file.startswith(f"video_{user_id}_{timestamp}"):
                        filepath = os.path.join(TEMP_DIR, file)

                        # Check file size
                        if os.path.getsize(filepath) > MAX_FILE_SIZE:
                            os.remove(filepath)
                            return {'success': False, 'error': 'file_too_large'}

                        return {
                            'success': True,
                            'filepath': filepath,
                            'filename': file,
                            'size': os.path.getsize(filepath)
                        }

                return {'success': False, 'error': 'file_not_found'}

        except yt_dlp.DownloadError as e:
            logger.error(f"yt-dlp download error: {e}")
            return {'success': False, 'error': 'download_failed'}
        except Exception as e:
            logger.error(f"Download error: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if user_id in self.downloading:
                self.downloading.remove(user_id)

    def cleanup_file(self, filepath: str):
        """Clean up downloaded file"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (URLs)"""
        message = update.message
        user_id = message.from_user.id

        if not message.text:
            return

        # Extract URL from message
        url = self.extract_url_from_text(message.text)

        if not url:
            await message.reply_text("❌ Link topilmadi. Video linkini yuboring.")
            return

        if not self.is_supported_url(url):
            await message.reply_text(MESSAGES['invalid_url'])
            return

        # Check if user is already downloading
        if user_id in self.downloading:
            await message.reply_text("⏳ Sizning boshqa videongiz yuklanmoqda. Iltimos kuting.")
            return

        # Show processing message
        status_msg = await message.reply_text(MESSAGES['processing'])

        # Get video info
        info = await self.get_video_info(url)

        if not info['success']:
            await status_msg.edit_text(MESSAGES['download_error'])
            return

        # Show video info and quality options
        video_info = f"📹 **{info['title']}**\n"
        if info['duration']:
            minutes = info['duration'] // 60
            seconds = info['duration'] % 60
            video_info += f"⏱ Davomiyligi: {minutes}:{seconds:02d}\n"
        if info['uploader']:
            video_info += f"👤 Kanal: {info['uploader']}\n"

        video_info += "\n🎯 Sifatni tanlang:"

        # Quality selection keyboard
        keyboard = [
            [InlineKeyboardButton("🔥 Eng yuqori sifat", callback_data=f"dl_best_{message.message_id}")],
            [InlineKeyboardButton("⚡ O'rta sifat (tez)", callback_data=f"dl_worst_{message.message_id}")],
            [InlineKeyboardButton("🎵 Faqat audio (MP3)", callback_data=f"dl_audio_{message.message_id}")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"cancel_{message.message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Store URL in context
        context.user_data[f'url_{message.message_id}'] = url

        await status_msg.edit_text(video_info, reply_markup=reply_markup, parse_mode='Markdown')

    async def handle_download_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle download quality selection"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = query.from_user.id

        if data.startswith('cancel_'):
            msg_id = data.split('_')[1]
            if f'url_{msg_id}' in context.user_data:
                del context.user_data[f'url_{msg_id}']
            await query.edit_message_text("❌ Bekor qilindi.")
            return

        if not data.startswith('dl_'):
            return

        parts = data.split('_')
        quality = parts[1]  # best, worst, audio
        msg_id = parts[2]

        # Get URL from context
        url = context.user_data.get(f'url_{msg_id}')
        if not url:
            await query.edit_message_text("❌ Link topilmadi. Qaytadan urinib ko'ring.")
            return

        # Check if user is already downloading
        if user_id in self.downloading:
            await query.answer("⏳ Sizning boshqa videongiz yuklanmoqda!", show_alert=True)
            return

        await query.edit_message_text(MESSAGES['downloading'])

        try:
            # Download video
            result = await self.download_video(url, quality, user_id)

            if not result['success']:
                error_msg = MESSAGES.get(result['error'], MESSAGES['download_error'])
                await query.edit_message_text(error_msg)
                return

            # Update status
            await query.edit_message_text(MESSAGES['uploading'])

            # Send file
            filepath = result['filepath']
            filename = result['filename']

            try:
                if quality == 'audio':
                    # Send as audio
                    with open(filepath, 'rb') as audio_file:
                        await context.bot.send_audio(
                            chat_id=query.message.chat_id,
                            audio=audio_file,
                            caption="🎵 Audio yuklandi!",
                            reply_to_message_id=query.message.message_id
                        )
                else:
                    # Send as video
                    with open(filepath, 'rb') as video_file:
                        await context.bot.send_video(
                            chat_id=query.message.chat_id,
                            video=video_file,
                            caption="🎬 Video yuklandi!",
                            reply_to_message_id=query.message.message_id,
                            supports_streaming=True
                        )

                await query.edit_message_text(MESSAGES['success'])

            except Exception as e:
                logger.error(f"File send error: {e}")
                await query.edit_message_text("❌ Faylni yuborishda xatolik. Fayl hajmi katta bo'lishi mumkin.")

            finally:
                # Clean up file
                self.cleanup_file(filepath)

        except Exception as e:
            logger.error(f"Download callback error: {e}")
            await query.edit_message_text(MESSAGES['download_error'])

        # Clean up context
        if f'url_{msg_id}' in context.user_data:
            del context.user_data[f'url_{msg_id}']

def main():
    """Main function"""
    if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("❌ BOT_TOKEN o'rnatilmagan!")
        print("Bot tokenini olish uchun @BotFather ga murojaat qiling.")
        print("Keyin BOT_TOKEN environment variable sifatida o'rnating:")
        print("export BOT_TOKEN='your_bot_token_here'")
        return

    print("🤖 Telegram Media Downloader Bot")
    print("=" * 40)

    # Create bot instance
    bot = MediaBot()

    # Create application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", bot.start_command))
    app.add_handler(CommandHandler("help", bot.help_command))
    app.add_handler(CallbackQueryHandler(bot.button_callback, pattern="^(help_|about|back)"))
    app.add_handler(CallbackQueryHandler(bot.handle_download_callback, pattern="^(dl_|cancel_)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    # Start bot
    print("🚀 Bot ishga tushmoqda...")
    print("📱 Telegram'da botingizni toping va /start bosing")
    print("🔗 Video linkini yuboring va yuklab oling!")
    print("\n⏹ To'xtatish uchun Ctrl+C bosing")

    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        print("\n👋 Bot to'xtatildi!")
    except Exception as e:
        print(f"❌ Xatolik: {e}")

if __name__ == '__main__':
    main()
