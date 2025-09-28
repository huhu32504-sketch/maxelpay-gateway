import requests
import json
import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

# Environment Configuration
environment = "prod"

# Load sensitive data from environment variables (recommended)
# For example, use: api_key = os.getenv("API_KEY")
api_key = "KbTNVOClfa4ctIIVO3syWiLmmKurls5x"
secret_key = "2H2ZXGtjw1SsR5WEOV26pQoqEcHrGRGi"
endpoint = f"https://api.maxelpay.com/v1/{environment}/merchant/order/checkout"

# Example payload data
payload_data = {
    "orderID": "113099",
    "amount": "100",
    "currency": "GBP",
    "timestamp": "1717666706",
    "userName": "ABC",
    "siteName": "Maxelpay",
    "userEmail": "abc@gmail.com",
    "redirectUrl": "https://example.com/checkout/order-received/113099/?key=order_IRZTHBRCp3pcg",
    "websiteUrl": "https://example.com",
    "cancelUrl": "https://example.com/cancel/cart-2/?cancel_order=true&order=order_IRZTHBRCp3pcg&order_id=113099&redirect=113099&_wpnonce=e1f09d926a",
    "webhookUrl": "http://example.com/wp-json/maxelpay/api/order_status"
}

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
        # Convert secret key to bytes
        secret_key = secret_key.encode("utf-8")
        if len(secret_key) != 32:
            raise ValueError("Secret key must be 32 bytes for AES-256")

        # Generate a random IV
        iv = os.urandom(16)

        # Convert payload to JSON and encode to bytes
        payload_bytes = json.dumps(payload_data).encode("utf-8")

        # Apply PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(payload_bytes) + padder.finalize()

        # Set up AES-CBC cipher
        cipher = Cipher(algorithms.AES(secret_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # Encrypt the data
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Combine IV and encrypted data, then encode to base64
        result = base64.b64encode(iv + encrypted_data).decode("utf-8")
        return result
    except Exception as e:
        raise Exception(f"Encryption failed: {str(e)}")

# Encrypt the payload
try:
    encrypted_result = encryption(secret_key, payload_data)
except Exception as e:
    print(f"Error during encryption: {e}")
    exit(1)

# Make API call
payload = json.dumps({"data": encrypted_result})
headers = {
    "api-key": api_key,
    "Content-Type": "application/json"
}

try:
    response = requests.post(endpoint, headers=headers, data=payload)
    response.raise_for_status()  # Raise an error for bad HTTP status codes
    print(response.text)
except requests.RequestException as e:
    print(f"API request failed: {e}")
