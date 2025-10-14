from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import logging
import re
import base64
import os
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for browser-based requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Razorpay API configuration
RAZORPAY_BASE_URL = "https://api.razorpay.com/v1/payments"
RAZORPAY_ORDER_URL = "https://api.razorpay.com/v1/orders"
KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_97K07Fs6vlYGkQ")  # Replace with your key_id
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")  # Set in Render environment variables

# Simplified headers for payment request
HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': f"Basic {base64.b64encode(f'{KEY_ID}:{KEY_SECRET}'.encode()).decode()}"
}

# Essential payment data
PAYMENT_DATA = {
    'amount': '100',  # 1 INR (100 paise)
    'currency': 'INR',
    'contact': '+918587992385',
    'email': 'khatrieex@gmail.com'
}

def validate_card_format(card_string):
    """Validate card format: card_number|exp_month|exp_year|cvv"""
    pattern = r'^\d{13,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$'
    if not re.match(pattern, card_string):
        return False
    try:
        number, exp_month, exp_year, cvv = card_string.split('|')
        exp_month = int(exp_month)
        exp_year = int(exp_year)
        cvv = int(cvv)
        if not (1 <= exp_month <= 12):
            return False
        if not (20 <= exp_year <= 99 or 2020 <= exp_year <= 2099):
            return False
        if not (100 <= cvv <= 9999):
            return False
        return True
    except ValueError:
        return False

def create_razorpay_order():
    """Create a new Razorpay order"""
    auth = base64.b64encode(f"{KEY_ID}:{KEY_SECRET}".encode()).decode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Basic {auth}"
    }
    data = {
        'amount': 100,  # 1 INR (100 paise)
        'currency': 'INR',
        'receipt': f'order_{int(time.time())}',
        'payment_capture': 1  # Auto-capture payment
    }
    try:
        response = requests.post(
            RAZORPAY_ORDER_URL,
            headers=headers,
            json=data,
            timeout=10
        )
        response.raise_for_status()
        order = response.json()
        logger.info(f"Created Razorpay order: {order}")
        return order.get('id')
    except requests.RequestException as e:
        logger.error(f"Failed to create Razorpay order: {str(e)}, Response: {e.response.text if e.response else 'No response'}")
        return None

def determine_status(response_text):
    """Determine the status based on the Razorpay response"""
    try:
        response_text = response_text.lower()
        if 'success' in response_text or 'captured' in response_text:
            return 'CHARGED', 'Payment Captured'
        elif 'authentication' in response_text or '3ds' in response_text:
            return '3DS', '3D Secure Authentication Required'
        elif 'declined' in response_text or 'failed' in response_text:
            return 'DECLINED', response_text
        elif 'incorrect' in response_text:
            return 'APPROVED', response_text  # e.g., incorrect CVV but card is live
        else:
            return 'DECLINED', response_text
    except Exception as e:
        logger.error(f"Error parsing response: {str(e)}")
        return 'DECLINED', f"Response parsing failed: {str(e)}"

@app.route('/gateway=razorpay0.10$', methods=['GET'])
def razorpay_check():
    """API endpoint to check card via Razorpay"""
    # Validate card details
    cc = request.args.get('cc')
    if not cc or not validate_card_format(cc):
        logger.error(f"Invalid card format: {cc}")
        return jsonify({
            'status': 'ERROR',
            'response': 'Invalid card format. Use: card_number|exp_month|exp_year|cvv',
            'gateway': 'Razorpay',
            'price': '1 INR'
        }), 400

    try:
        number, exp_month, exp_year, cvv = cc.split('|')
        # Normalize year to two digits
        if len(exp_year) == 4:
            exp_year = exp_year[2:]
    except Exception as e:
        logger.error(f"Error parsing card details: {cc}, Error: {str(e)}")
        return jsonify({
            'status': 'ERROR',
            'response': 'Invalid card format',
            'gateway': 'Razorpay',
            'price': '1 INR'
        }), 400

    # Step 1: Create a new Razorpay order
    order_id = create_razorpay_order()
    if not order_id:
        logger.error("Failed to create Razorpay order")
        return jsonify({
            'status': 'ERROR',
            'response': 'Failed to create Razorpay order',
            'gateway': 'Razorpay',
            'price': '1 INR'
        }), 500

    # Step 2: Create payment
    payment_data = PAYMENT_DATA.copy()
    payment_data.update({
        'method': 'card',
        'card': {
            'number': number,
            'cvv': cvv,
            'name': 'Test User',
            'expiry_month': exp_month,
            'expiry_year': exp_year
        },
        'order_id': order_id
    })

    try:
        response = requests.post(
            RAZORPAY_BASE_URL,
            headers=HEADERS,
            json=payment_data,
            timeout=30
        )
        logger.info(f"Payment creation response: {response.status_code}, {response.text}")
        status, message = determine_status(response.text)

        return jsonify({
            'status': status,
            'response': message,
            'gateway': 'Razorpay',
            'price': '1 INR'
        })

    except requests.RequestException as e:
        logger.error(f"Payment creation failed: {str(e)}, Response: {e.response.text if e.response else 'No response'}")
        return jsonify({
            'status': 'DECLINED',
            'response': f"Request failed: {str(e)}",
            'gateway': 'Razorpay',
            'price': '1 INR'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
