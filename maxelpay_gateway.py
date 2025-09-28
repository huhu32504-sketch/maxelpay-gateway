''' Encryption Method: We need to install a cryptography package for encryption.

Step 1:- pip install cryptography 
Step 2:- pip install requests '''
 
import requests
import json
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends  import default_backend 

''' Environment Configuration:
 - stg: Sandbox environment used for testing and development.
  - prod: Live environment for production use. 
'''
environment = "prod" 

''' Note: Please replace api_key and secret_key with your original API Key and API Secret respectively.
Click here https://dashboard.maxelpay.com/developers to obtain the API Key and API Secret. '''

const api_key    = "KbTNVOClfa4ctIIVO3syWiLmmKurls5x";
const secret_key = "2H2ZXGtjw1SsR5WEOV26pQoqEcHrGRGi";
endpoint = "https://api.maxelpay.com/v1/{}/merchant/order/checkout".format(environment) 

''' Payload: An example payload data is:- '''

payload_data = {
   "orderID"     : "113099",
   "amount"      : "100",
   "currency"    : "USD",
   "timestamp"   : "1717666706",
   "userName"    : "ABC",
   "siteName"    : "Maxelpay",
   "userEmail"   : "abc@gmail.com",
   "redirectUrl" : "https://example.com/checkout/order-received/113099/?key=order_IRZTHBRCp3pcg",
   "websiteUrl"  : "https://example.com",
   "cancelUrl"   : "https://example.com/cancel/cart-2/?cancel_order=true&order=order_IRZTHBRCp3pcg&order_id=113099&redirect=113099&_wpnonce=e1f09d926a",
   "webhookUrl"  : "http://example.com/wp-json/maxelpay/api/order_status"
} 

''' Function Start '''

def encryption(secret_key, payload_data):

  """ Convert to bytes """
  iv = secret_key[:16].encode("utf-8")

  """ Convert to bytes """
  secret_key = secret_key.encode("utf-8")  
  
  """ Pad data to match the block size """
  block_size = 256
  padded_data = json.dumps(payload_data).encode("utf-8")
  padded_data += b' ' * (block_size - len(padded_data) %   block_size)
  backend = default_backend()
  cipher = Cipher(algorithms.AES(secret_key), modes.CBC(iv),  backend=backend) 
  encryptor = cipher.encryptor()
  encrypted_data = encryptor.update(padded_data) + encryptor.finalize() 
  result = base64.b64encode(encrypted_data).decode("utf-8")

  return result 

''' Function End '''

encrypted_result = encryption( secret_key, payload_data )

''' API Call '''

payload = json.dumps({'data': encrypted_result})

headers = {
"api-key": api_key,
"Content-Type": "application/json"
} 
response = requests.request("POST", endpoint, headers = headers,
data = payload)
print(response.text)
