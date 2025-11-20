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
import os

app = Flask(__name__)

# Set up rate limiting with the correct initialization for newer flask-limiter versions
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
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

def extract_result_from_response(response_text, amount, currency):
    """Extract result from response text"""
    try:
        res_json = json.loads(response_text)
        
        # Check if there are errors in the response
        if 'data' in res_json and 'submitForCompletion' in res_json['data']:
            submit_data = res_json['data']['submitForCompletion']
            
            # Check for errors
            if 'errors' in submit_data and submit_data['errors']:
                error_codes = [error.get('code', '') for error in submit_data['errors']]
                
                # Handle specific error codes
                if 'DELIVERY_NO_DELIVERY_STRATEGY_AVAILABLE' in error_codes:
                    return f"AMOUNT: ${amount}\nRESULT: DELIVERY_UNAVAILABLE"
                elif 'PAYMENTS_UNACCEPTABLE_PAYMENT_AMOUNT' in error_codes:
                    return f"AMOUNT: ${amount}\nRESULT: PAYMENT_AMOUNT_ERROR"
                elif 'REQUIRED_ARTIFACTS_UNAVAILABLE' in error_codes:
                    return f"AMOUNT: ${amount}\nRESULT: ARTIFACTS_UNAVAILABLE"
                else:
                    return f"AMOUNT: ${amount}\nRESULT: ERROR: {'; '.join(error_codes)}"
            
            # Check for successful receipt
            if 'receipt' in submit_data and submit_data['receipt']:
                receipt = submit_data['receipt']
                if 'id' in receipt:
                    return f"AMOUNT: ${amount}\nRESULT: ORDER_PLACED"
        
        # Fallback to searching for specific patterns in response
        if "shopify_payments" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: ORDER_PLACED"
        elif "CARD_DECLINED" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: CARD_DECLINED"
        elif "INCORRECT_NUMBER" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: INCORRECT_NUMBER"
        elif "GENERIC_ERROR" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: GENERIC_ERROR"
        elif "AUTHENTICATION_FAILED" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: 3DS_REQUIRED"
        elif "FRAUD_SUSPECTED" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: FRAUD_SUSPECTED"
        elif "INCORRECT_ADDRESS" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: MISMATCHED_BILLING"
        elif "INCORRECT_ZIP" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: MISMATCHED_ZIP"
        elif "INCORRECT_PIN" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: MISMATCHED_PIN"
        elif "insufficient_funds" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: INSUFFICIENT_FUNDS"
        elif "INSUFFICIENT_FUNDS" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: INSUFFICIENT_FUNDS"
        elif "INVALID_CVC" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: INVALID_CVC"
        elif "INCORRECT_CVC" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: INCORRECT_CVC"
        elif "CompletePaymentChallenge" in str(res_json):
            return f"AMOUNT: ${amount}\nRESULT: 3DS_REQUIRED"
        else:
            return f"AMOUNT: ${amount}\nRESULT: UNKNOWN_ERROR"
            
    except Exception as e:
        return f"AMOUNT: ${amount}\nRESULT: ERROR: {str(e)}"

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
    # Use port from environment variable for cloud deployment compatibility
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
