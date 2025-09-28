import os
from flask import Flask, request, redirect, render_template_string
import requests
import json
import hmac
import hashlib
import time
import uuid
import re
import logging


app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    <h1>Pay with Crypto Magic!</h1>
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

# Environment-based configuration
ENV = 'stg'  # Hardcode to staging to avoid prod issues
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
API_URL = 'https://api.maxelpay.com/v1/stg/merchant/order/checkout'
PRODUCT_ID = os.environ.get('PRODUCT_ID', 'default_product')  # Set in MaxelPay dashboard

# Optional wallet address
WALLET_ADDRESS = os.environ.get('WALLET_ADDRESS', '0xEF08ECD78FEe6e7104cd146F5304cEb55d1862Bb')
CURRENCY = 'GBP'
CRYPTO_CURRENCY = 'ETH'

# Validate required environment variables
if not all([API_KEY, API_SECRET]):
    error_message = f"Missing required environment variables for ENV={ENV}. Check API_KEY and API_SECRET in Render."
    logging.error(error_message)

# MaxelPay Signature Function (HMAC SHA256)
def generate_signature(secret, payload_str):
    return hmac.new(secret.encode('utf-8'), payload_str.encode('utf-8'), hashlib.sha256).hexdigest()

# Basic email validation
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

# Create payload for MaxelPay API
def create_payload(user_name, user_email, amount):
    order_id = str(uuid.uuid4())[:8]
    timestamp = int(time.time())
    payload_dict = {
        "publicKey": API_KEY,
        "uniqueUserId": user_email,
        "productId": PRODUCT_ID,  # Use configurable product ID
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
    return payload_dict

@app.route('/')
def home():
    if not all([API_KEY, API_SECRET]):
        return render_template_string(FORM_HTML, message="Server configuration error: Missing API credentials. Contact support.", success=False)
    return render_template_string(FORM_HTML)

@app.route('/process_payment', methods=['POST'])
@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))  # Retry 3 times, 2s delay
def process_payment():
    try:
        user_name = request.form['userName'].strip()
        user_email = request.form['userEmail'].strip()
        amount = float(request.form['amount'])

        # Validate inputs
        if not user_name or len(user_name) > 100:
            return render_template_string(FORM_HTML, message="Invalid name provided.", success=False)
        if not is_valid_email(user_email):
            return render_template_string(FORM_HTML, message="Invalid email format.", success=False)
        if amount < 1:
            return render_template_string(FORM_HTML, message="Amount must be at least 1 GBP.", success=False)

        # Create payload
        payload_dict = create_payload(user_name, user_email, amount)
        payload_str = json.dumps(payload_dict, sort_keys=True, separators=(',', ':'))  # Compact JSON
        signature = generate_signature(API_SECRET, payload_str)

        # Debug logs
        logging.info(f"ENV: {ENV}, API_URL: {API_URL}")
        logging.info(f"Payload: {payload_str}")
        logging.info(f"Signature: {signature}")
        logging.info(f"API_KEY (partial): {API_KEY[:10]}...")

        # Add signature to payload
        payload_dict["signature"] = signature

        # Send to MaxelPay API
        headers = {'Content-Type': 'application/json'}
        response = requests.post(API_URL, headers=headers, json=payload_dict)
        response.raise_for_status()
        resp_json = response.json()

        logging.info(f"MaxelPay response: {resp_json}")

        if 'checkout_url' in resp_json:
            return redirect(resp_json['checkout_url'])
        else:
            error_msg = resp_json.get('error', 'Unknown error from MaxelPay')
            logging.error(f"API error: {error_msg}")
            return render_template_string(FORM_HTML, message=error_msg, success=False)

    except KeyError:
        logging.error("Missing form fields")
        return render_template_string(FORM_HTML, message="Missing required form fields.", success=False)
    except ValueError as e:
        logging.error(f"Invalid input: {str(e)}")
        return render_template_string(FORM_HTML, message=f"Invalid input: {str(e)}", success=False)
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error: {str(e)}")
        error_msg = f"Payment Gateway Error: {str(e)}"
        if "401" in str(e):
            error_msg += " (Check API credentials or contact MaxelPay support)"
        return render_template_string(FORM_HTML, message=error_msg, success=False)
    except requests.exceptions.RequestException as e:
        logging.error(f"Network Error: {str(e)}")
        return render_template_string(FORM_HTML, message=f"Network Error: {str(e)}", success=False)
    except Exception as e:
        logging.error(f"Unexpected Error: {str(e)}")
        return render_template_string(FORM_HTML, message=f"Unexpected Error: {str(e)}", success=False)

@app.route('/success')
def success():
    return '<h1>Payment Successful! Check your wallet for crypto.</h1>'

@app.route('/cancel')
def cancel():
    return '<h1>Payment Canceled. Try again?</h1>'

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        logging.info(f"Webhook received: {data}")
        return 'OK', 200
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return 'Error', 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Render sets PORT
    app.run(debug=False, host='0.0.0.0', port=port)
