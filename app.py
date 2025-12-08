from flask import Flask, request, jsonify, Response
import requests
import time

app = Flask(__name__)

# Configuration
BRAINTREE_API_URL = 'https://www.md-tech-gen.tech/api/braintree/b3auth2.php'
TIMEOUT = 60  # 60 seconds timeout

# Cookies and headers as provided
cookies = {
    'PHPSESSID': 'rv0evssknbthvkijjfvit0086t',
}

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.md-tech-gen.tech/app/checkers',
    'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
}

@app.route('/gate=b3/cc=<card_details>', methods=['GET'])
def process_payment(card_details):
    try:
        # Parse card details from the URL parameter
        parts = card_details.split('|')
        
        if len(parts) < 3:
            return jsonify({"error": "Invalid card details format"}), 400
            
        card_number = parts[0]
        month = parts[1]
        year = parts[2]
        cvv = parts[3] if len(parts) > 3 else ''
        
        # Format the cc parameter as required by the API
        cc_param = f"{card_number}|{month}|{year}"
        if cvv:
            cc_param += f"|{cvv}"
            
        # Prepare the parameters for the API request
        params = {
            'cc': cc_param,
            'useProxy': '0',
            'hitSender': 'both',
            'site': '',
        }
        
        # Make the request with timeout
        response = requests.get(
            BRAINTREE_API_URL,
            params=params,
            cookies=cookies,
            headers=headers,
            timeout=TIMEOUT
        )
        
        # If the API returns a successful response (200), filter to show only status and response
        if response.status_code == 200:
            data = response.json()
            result = {
                "status": data.get("status", ""),
                "response": data.get("response", "")
            }
            return jsonify(result)
        else:
            # For any other status code (including 502), return the raw response
            return Response(
                response.content,
                status=response.status_code,
                headers=dict(response.headers)
            )
            
    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Request timed out after 60 seconds",
            "details": "The payment gateway did not respond in time. Please try again."
        }), 504
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Payment gateway connection failed",
            "details": str(e)
        }), 503
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
