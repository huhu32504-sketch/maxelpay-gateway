import os
from flask import Flask, request, redirect, render_template_string
import requests
import json
import hmac
import hashlib
from Crypto.Util.Padding import pad  # Keep if needed elsewhere, but not for signature
import base64
import time
import uuid

app = Flask(__name__)

# Environment-based configuration (keep your existing ENV, API_KEY, etc.)
ENV = os.environ.get('ENV', 'stg') # Default to sandbox
if ENV == 'prod':
    API_KEY = os.environ.get('API_KEY_PROD')
    API_SECRET = os.environ.get('API_SECRET_PROD')
    API_URL = 'https://api.maxelpay.com/v1/prod/merchant/order/checkout'
else:
    API_KEY = os.environ.get('API_KEY')
    API_SECRET = os.environ.get('API_SECRET')
    API_URL = 'https://api.maxelpay.com/v1/stg/merchant/order/checkout'

# Validate keys early
if not all([API_KEY, API_SECRET, WALLET_ADDRESS]):
    raise ValueError(f"Missing required environment variables for ENV={ENV}. Check API_KEY, API_SECRET, and WALLET_ADDRESS.")

WALLET_ADDRESS = os.environ.get('WALLET_ADDRESS', '0xEF08ECD78FEe6e7104cd146F5304cEb55d1862Bb')  # Optional
CURRENCY = 'GBP'
CRYPTO_CURRENCY = 'ETH'

# MaxelPay Signature Function (HMAC SHA256)
def generate_signature(secret, payload_str):
    return hmac.new(secret.encode('utf-8'), payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

# ... Keep FORM_HTML as is ...

@app.route('/process_payment', methods=['POST'])
def process_payment():
    user_name = request.form['userName']
    user_email = request.form['userEmail']
    amount = float(request.form['amount'])

     Simple HTML form (grandma-friendly: big buttons, clear labels)
FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Pay with Card - MaxelPay Gateway</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f4f4f4; }
        input { padding: 15px; margin: 10px; width: 250px; font-size: 16px; border: 1px solid #ccc; border-radius: 5px; }
        button { padding: 15px 30px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 18px; }
        button:hover { background: #0056b3; }
        h1 { color: #333; }
    </style>
</head>
<body>
    <h1>Pay and Get Crypto Magic!</h1>
    <p>Enter details below. We'll convert your card payment to crypto automatically.</p>
    <form method="post" action="/process_payment">
        <input type="text" name="userName" placeholder="Your Name" required><br>
        <input type="email" name="userEmail" placeholder="Your Email" required><br>
        <input type="number" name="amount" placeholder="Amount in GBP (e.g., 10.00)" step="0.01" min="1" required><br>
        <button type="submit">Pay with Card Now</button>
    </form>
    {% if message %}
        <p style="color: {{ 'green' if success else 'red' }}; font-size: 18px;">{{ message }}</p>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(FORM_HTML)
    # Build payload (match MaxelPay format)
    order_id = str(uuid.uuid4())[:8]
    timestamp = int(time.time())
    payload_dict = {
        "publicKey": API_KEY,  # Use your API key as publicKey
        "uniqueUserId": user_email,  # Or generate unique ID
        "productId": "default_product",  # Customize or create in MaxelPay dashboard
        "amount": f"{amount:.2f}",
        "currency": CURRENCY,
        "timestamp": timestamp,
        "siteName": "kspayments",
        "userName": user_name,
        "redirectUrl": "https://maxelpay-gateway.onrender.com/success",
        "websiteUrl": "https://maxelpay-gateway.onrender.com",
        "cancelUrl": "https://maxelpay-gateway.onrender.com/cancel",
        "webhookUrl": "https://maxelpay-gateway.onrender.com/webhook"
    }
    payload_str = json.dumps(payload_dict, sort_keys=True)  # Sort for consistent signature
    signature = generate_signature(API_SECRET, payload_str)

    # Add signature to payload
    payload_dict["signature"] = signature

    # Send to MaxelPay API (JSON, no encryption)
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload_dict)
        response.raise_for_status()
        resp_json = response.json()
        
        if 'checkout_url' in resp_json:
            return redirect(resp_json['checkout_url'])
        else:
            error_msg = resp_json.get('error', 'Unknown error from MaxelPay')
            return render_template_string(FORM_HTML, message=error_msg, success=False)
    except requests.exceptions.HTTPError as e:
        return render_template_string(FORM_HTML, message=f'HTTP Error: {str(e)}', success=False)
    except requests.exceptions.RequestException as e:
        return render_template_string(FORM_HTML, message=f'Network Error: {str(e)}', success=False)
    except ValueError as e:
        return render_template_string(FORM_HTML, message=f'JSON Error: {str(e)}', success=False)
    except Exception as e:
        return render_template_string(FORM_HTML, message=f'Unexpected Error: {str(e)}', success=False)

# ... Keep other routes as is ...
@app.route('/success')
def success():
    return '<h1>Payment Successful! Check your wallet for crypto.</h1>'

@app.route('/cancel')
def cancel():
    return '<h1>Payment Canceled. Try again?</h1>'

@app.route('/webhook', methods=['POST'])  # Optional: Handle status updates
def webhook():
    # Log or process: e.g., print(request.json)
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Render sets PORT
    app.run(debug=False, host='0.0.0.0', port=port)  # debug=False for prod
