import os, json, hashlib, base64
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from fido2.webauthn import AuthenticatorData, AttestedCredentialData
from fido2.cose import ES256
import cbor2

try:
    rp_id = "github.com"
    challenge_b64 = "test_challenge"
    
    private_key = ec.generate_private_key(ec.SECP256R1())
    cose_key = ES256.from_cryptography_key(private_key.public_key())
    credential_id = os.urandom(32)
    
    client_data = json.dumps({
        "type": "webauthn.create",
        "challenge": challenge_b64,
        "origin": "https://github.com",
        "crossOrigin": False
    }).encode('utf-8')
    
    rp_id_hash = hashlib.sha256(rp_id.encode('utf-8')).digest()
    flags = 0x41
    acd = AttestedCredentialData.create(
        aaguid=b'\x00'*16,
        credential_id=credential_id,
        public_key=cose_key
    )
    auth_data = AuthenticatorData.create(rp_id_hash, flags, 0, acd)
    
    att_obj = cbor2.dumps({
        "fmt": "none",
        "attStmt": {},
        "authData": auth_data
    })
    print("SUCCESS!")
except Exception as e:
    import traceback
    traceback.print_exc()
