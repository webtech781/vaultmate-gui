import cbor2
import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from fido2.cose import ES256
from fido2.webauthn import AuthenticatorData, AttestedCredentialData

rp_id = "github.com"
private_key = ec.generate_private_key(ec.SECP256R1())
cose_key = ES256.from_cryptography_key(private_key.public_key())
credential_id = b'1234567890123456'

rp_id_hash = hashlib.sha256(rp_id.encode('utf-8')).digest()
acd = AttestedCredentialData.create(b'\x00'*16, credential_id, cose_key)
auth_data = AuthenticatorData.create(rp_id_hash, 0x41, 0, acd)

try:
    att_obj = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
    print("Success!", len(att_obj))
except Exception as e:
    print("Error:", e)
