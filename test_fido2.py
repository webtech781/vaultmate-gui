import cbor2
from fido2.webauthn import AuthenticatorData
import sys

# Create empty auth data
auth_data = AuthenticatorData(b'\x00'*32, 0x41, 0)
try:
    dumped = cbor2.dumps({"authData": auth_data})
    print("Dumped:", dumped)
    # Check if authData is actually serialized as a byte string
    decoded = cbor2.loads(dumped)
    print("Decoded type:", type(decoded["authData"]))
except Exception as e:
    print("Error:", e)
