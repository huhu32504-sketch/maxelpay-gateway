from flask import Flask, request, redirect, render_template_string
import requests
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import base64
import time
import uuid  # For unique order IDs

app = Flask(__name__)

# Replace with your MaxelPay details
API_KEY = 'KbTNVOClfa4ctIIVO3syWiLmmKurls5x'
API_SECRET = '2H2ZXGtjw1SsR5WEOV26pQoqEcHrGRGi'  # Used for encryption
WALLET_ADDRESS = '0xEF08ECD78FEe6e7104cd146F5304cEb55d1862Bb'  # Set in dashboard, but not in payload
API_URL = 'https://api.maxelpay.com/v1/prod/merchant/order/checkout'  # Use /prod/ for sandbox
CURRENCY = 'GBP'  # Fiat currency for customer payment
CRYPTO_CURRENCY = 'ETH'  # You receive this (set in dashboard)

# Encryption function (AES CBC with secret as key/IV)
def encrypt_payload(secret, payload):
    key = secret.encode('utf-8')[:32]  # AES-256 key (first 32 bytes)
    iv = secret.encode('utf-8')[:16]   # First 16 bytes as IV
    cipher = AES.new(key, AES.MODE_CBC, iv)
    json_payload = json.dumps(payload).encode('utf-8')
    ciphertext = cipher.encrypt(pad(json_payload, AES.block_size))
    return base64.b64encode(ciphertext).decode('utf-8')

# Simple HTML form (grandma-friendly: big buttons, clear labels)
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

@app.route('/process_payment', methods=['POST'])
def process_payment():
    user_name = request.form['userName']
    user_email = request.form['userEmail']
    amount = request.form['amount']

    # Build payload
    order_id = str(uuid.uuid4())[:8]  # Simple unique ID
    timestamp = int(time.time())
    payload = {
        "orderID": order_id,
        "amount": amount,
        "currency": CURRENCY,
        "timestamp": timestamp,
        "userName": user_name,
        "siteName": "My Simple Store",  # Customize
        "userEmail": user_email,
        "redirectUrl": "http://localhost:5001/success",  # Your success page (or external URL)
        "websiteUrl": "http://localhost:5001",  # Your site URL
        "cancelUrl": "http://localhost:5001/cancel",  # Cancel page
        "webhookUrl": "http://localhost:5001/webhook"  # Optional: For status updates
    }

    # Encrypt payload
    encrypted = encrypt_payload(API_SECRET, payload)

    # Send to MaxelPay API
    headers = {
        'Content-Type': 'application/json',
        'api-key': API_KEY
    }
    data = {'encrypted_payload': encrypted}  # Assuming this format; check docs if needed
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        resp_json = response.json()
        
        if response.status_code == 200 and 'checkout_url' in resp_json:  # Assume response has this
            # Redirect to hosted checkout
            return redirect(resp_json['checkout_url'])
        else:
            error_msg = resp_json.get('error', 'Unknown error')
            return render_template_string(FORM_HTML, message=error_msg, success=False)
    except Exception as e:
        return render_template_string(FORM_HTML, message=f'Error: {str(e)}', success=False)

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
    app.run(debug=True, host='0.0.0.0', port=5001)