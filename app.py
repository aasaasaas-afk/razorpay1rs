import asyncio
import re
import json
from flask import Flask, request, jsonify
from msh import get_variant_and_token
import threading
import time
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

# Set up rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def parse_proxy_string(proxy_str):
    """Parse proxy string in format host:user:pass:ip"""
    if not proxy_str:
        return None
        
    parts = proxy_str.split(':')
    if len(parts) < 4:
        return None
        
    return {
        'host': parts[0],
        'user': parts[1],
        'password': parts[2],
        'ip': ':'.join(parts[3:])  # Handle case where IP might contain colons (IPv6)
    }

def parse_cc_string(cc_str):
    """Parse credit card string in format number|month|year|cvv"""
    if not cc_str:
        return None
        
    parts = cc_str.split('|')
    if len(parts) < 4:
        return None
        
    return {
        'number': parts[0],
        'month': parts[1],
        'year': parts[2],
        'cvv': parts[3]
    }

@app.route('/checkout', methods=['GET'])
@limiter.limit("10 per minute")
def checkout():
    try:
        # Get query parameters
        site = request.args.get('site')
        cc_str = request.args.get('cc')
        proxy_str = request.args.get('proxy')
        
        # Validate required parameters
        if not site or not cc_str:
            return jsonify({"error": "Missing required parameters: site and cc"}), 400
        
        # Parse credit card info
        cc_info = parse_cc_string(cc_str)
        if not cc_info:
            return jsonify({"error": "Invalid credit card format. Expected: number|month|year|cvv"}), 400
        
        # Parse proxy info (optional)
        proxy_info = None
        if proxy_str:
            proxy_info = parse_proxy_string(proxy_str)
            if not proxy_info:
                return jsonify({"error": "Invalid proxy format. Expected: host:user:pass:ip"}), 400
        
        # Add protocol if missing
        if not site.startswith(('http://', 'https://')):
            site = 'https://' + site
            
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                get_variant_and_token(site, cc_info['number'], cc_info['month'], cc_info['year'], cc_info['cvv'])
            )
            return jsonify({"result": result})
        finally:
            loop.close()
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
