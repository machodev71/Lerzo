import hmac
import hashlib

webhook_secret = 'V8$ePqL9!x@1RzW5#n^K3tY7&uF0jG2'  # Now properly quoted
payload = open('test_payload.json').read()

signature = hmac.new(
    webhook_secret.encode('utf-8'),
    payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print(f"X-Razorpay-Signature: {signature}")