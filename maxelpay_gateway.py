import os
import json
import base64
import requests
import uuid
import time
import logging
from flask import Flask, request, redirect, render_template_string
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Simple HTML form
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
ENV = os.environ.get('ENV', 'stg')  # Default to staging
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
API_URL = f"https://api.maxelpay.com/v1/{ENV}/merchant/order/checkout"

# Validate environment variables
if not all([API_KEY, API_SECRET]):
    error_message = f"Missing required environment variables for ENV={ENV}. Check API_KEY and API_SECRET in Render."
    logging.error(error_message)

def encryption(secret_key, payload_data):
    """
    Encrypts the payload data using AES-256-CBC with PKCS7 padding.
    
    Args:
        secret_key (str): The secret key for encryption (must be 32 bytes when encoded).
        payload_data (dict): The data to encrypt.
    
    Returns:
        str: Base64-encoded string containing the IV and encrypted data.
    """
    try:
        secret_key = secret_key.encode("utf-8")
        if len(secret_key) != 32:
            raise ValueError("Secret key must be 32 bytes for AES-256")
        iv = os.urandom(16)
        payload_bytes = json.dumps(payload_data).encode("utf-8")
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(payload_bytes) + padder.finalize()
        cipher = Cipher(algorithms.AES(secret_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        return base64.b64encode(iv + encrypted_data).decode("utf-8")
    except Exception as e:
        raise Exception(f"Encryption failed: {str(e)}")

def create_payload(user_name, user_email, amount):
    order_id = str(uuid.uuid4())[:8]
    timestamp = int(time.time())
    return {
        "orderID": order_id,
        "amount": f"{amount:.2f}",
        "currency": "GBP",
        "timestamp": str(timestamp),
        "userName": user_name,
        "siteName": "Maxelpay",
        "userEmail": user_email,
        "redirectUrl": "https://maxelpay-gateway.onrender.com/success",
        "websiteUrl": "https://maxelpay-gateway.onrender.com",
        "cancelUrl": "https://maxelpay-gateway.onrender.com/cancel",
        "webhookUrl": "https://maxelpay-gateway.onrender.com/webhook"
    }

@app.route('/')
def home():
    if not all([API_KEY, API_SECRET]):
        return render_template_string(FORM_HTML, message="Server configuration error: Missing API credentials. Contact support.", success=False)
    return render_template_string(FORM_HTML)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    try:
        user_name = request.form['userName'].strip()
        user_email = request.form['userEmail'].strip()
        amount = float(request.form['amount'])

        if not user_name or len(user_name) > 100:
            return render_template_string(FORM_HTML, message="Invalid name provided.", success=False)
        if not re.match(r"[^@]+@[^@]+\.[^@]+", user_email):
            return render_template_string(FORM_HTML, message="Invalid email format.", success=False)
        if amount < 1:
            return render_template_string(FORM_HTML, message="Amount must be at least 1 GBP.", success=False)

        payload_data = create_payload(user_name, user_email, amount)
        logging.info(f"Payload before encryption: {json.dumps(payload_data, sort_keys=True)}")

        encrypted_result = encryption(API_SECRET, payload_data)
        payload = json.dumps({"data": encrypted_result})
        headers = {
            "api-key": API_KEY,
            "Content-Type": "application/json"
        }

        logging.info(f"ENV: {ENV}, API_URL: {API_URL}")
        logging.info(f"Encrypted payload: {payload}")
        logging.info(f"API_KEY (partial): {API_KEY[:10]}...")

        response = requests.post(API_URL, headers=headers, data=payload)
        try:
            resp_json = response.json()
        except ValueError:
            resp_json = {"error": "Invalid JSON response from MaxelPay"}
        logging.info(f"MaxelPay response: {resp_json}")
        logging.info(f"Response status: {response.status_code}, headers: {response.headers}")

        response.raise_for_status()

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
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)
