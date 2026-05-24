#!/usr/bin/env python3
import sys
import json
import traceback
import struct
import os
import tkinter as tk
from tkinter import simpledialog, messagebox
import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.hashes import SHA256
import cbor2
from fido2.webauthn import AuthenticatorData, AttestedCredentialData
from fido2.cose import ES256

# Add current dir to path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import Database
from crypto_utils import get_from_keyring

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vaultmate_config.json")

def get_message():
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        sys.exit(0)
    message_length = struct.unpack('@I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def send_message(message):
    encoded_message = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('@I', len(encoded_message)))
    sys.stdout.buffer.write(encoded_message)
    sys.stdout.buffer.flush()

def get_active_user():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            username = config.get("last_username")
            if not username:
                return None
            password = get_from_keyring(username)
            if not password:
                return None
                
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vaultmate.db")
            db = Database(db_path)
            user = db.login(username, password)
            if not user:
                return None
            return db, user
    except Exception:
        return None

def log_error(msg):
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log"), "a") as f:
            f.write(msg + "\n")
    except:
        pass

def main():
    while True:
        try:
            msg = get_message()
            action = msg.get("action")
            
            auth = get_active_user()
            if not auth:
                send_message({"error": "VaultMate is locked or not configured for OS Auto-Login."})
                continue
                
            db, user = auth
            
            if action == "autofill_request":
                url = msg.get("url", "").lower()
                passwords = db.get_web_passwords(user['id'], user['key'])
                
                matches = []
                for p in passwords:
                    # Simple matching: if the saved URL is inside the current URL
                    saved_domain = p['web_url'].replace('https://','').replace('http://','').split('/')[0].lower()
                    if saved_domain in url:
                        matches.append({
                            "username": p['username'],
                            "password": p['password']
                        })
                
                send_message({
                    "status": "success",
                    "credentials": matches
                })
                
            elif action == "auto_save":
                url = msg.get("url")
                name = msg.get("name")
                username = msg.get("username")
                password = msg.get("password")
                
                existing = db.get_web_passwords(user['id'], user['key'])
                exists = False
                update_pid = None
                
                for p in existing:
                    # check if domain matches and username matches
                    saved_domain = p['web_url'].replace('https://','').replace('http://','').split('/')[0].lower()
                    current_domain = url.replace('https://','').replace('http://','').split('/')[0].lower()
                    
                    if saved_domain in current_domain or current_domain in saved_domain:
                        if p['username'] == username:
                            if p['password'] == password:
                                exists = True
                            else:
                                update_pid = p['id']
                            break
                            
                if not exists and not update_pid:
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    save = messagebox.askyesno("VaultMate - AutoSave", f"Do you want to save the new password for {name} ({username})?", parent=root)
                    if save:
                        db.add_web_password(user['id'], url, name, username, password, "", user['key'])
                    root.destroy()
                elif update_pid:
                    root = tk.Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    save = messagebox.askyesno("VaultMate - Update Password", f"Your password for {name} ({username}) has changed. Do you want to update it in VaultMate?", parent=root)
                    if save:
                        db.update_web_password(update_pid, user['id'], url, name, username, password, "", user['key'])
                    root.destroy()
                
                send_message({"status": "success"})
                
            elif action == "passkey_create":
                options = msg.get("options", {}).get("publicKey", {})
                rp_id = options.get("rp", {}).get("id", "unknown")
                user_name = options.get("user", {}).get("name", "unknown")
                
                # Decode challenge and user.id from custom serialization
                challenge_b64 = options.get("challenge", {}).get("data", "")
                user_id_b64 = options.get("user", {}).get("id", {}).get("data", "")
                
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                # Vault is already unlocked via OS keyring in get_active_user().
                # Just ask for user presence / authorization.
                authorized = messagebox.askyesno("VaultMate - Passkey", 
                                                 f"Create a Passkey for {rp_id} ({user_name})?\nClick Yes to authorize.", 
                                                 parent=root)
                root.destroy()
                
                if not authorized:
                    send_message({"error": "User cancelled passkey creation"})
                    continue
                    
                # 1. Generate Key
                private_key = ec.generate_private_key(ec.SECP256R1())
                cose_key = ES256.from_cryptography_key(private_key.public_key())
                credential_id = os.urandom(32)
                
                # 2. Store in DB
                priv_bytes = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                pub_bytes = private_key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                # 3. Store passkey in database
                db.add_passkey(user['id'], rp_id, user_name, credential_id.hex(), pub_bytes, priv_bytes, user['key'], user_id_b64)
                
                # 3. Construct ClientDataJSON
                client_data = json.dumps({
                    "type": "webauthn.create",
                    "challenge": challenge_b64,
                    "origin": msg.get("url").split('/')[0] + "//" + msg.get("url").split('/')[2],
                    "crossOrigin": False
                }).encode('utf-8')
                
                # 4. Construct AttestationObject
                rp_id_hash = hashlib.sha256(rp_id.encode('utf-8')).digest()
                flags = 0x45 # UP=1, UV=1, AT=1
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
                
                def b64u(b):
                    return base64.urlsafe_b64encode(b).decode('ascii').rstrip('=')
                
                cred_response = {
                    "id": b64u(credential_id),
                    "rawId": {"__type": "ArrayBuffer", "data": b64u(credential_id)},
                    "response": {
                        "clientDataJSON": {"__type": "ArrayBuffer", "data": b64u(client_data)},
                        "attestationObject": {"__type": "ArrayBuffer", "data": b64u(att_obj)},
                        "authenticatorData": {"__type": "ArrayBuffer", "data": b64u(auth_data)}
                    },
                    "type": "public-key"
                }
                
                send_message({"credential": cred_response})

            elif action == "passkey_get":
                options = msg.get("options", {}).get("publicKey", {})
                rp_id = options.get("rpId", msg.get("url", "//unknown").split('/')[2])
                challenge_b64 = options.get("challenge", {}).get("data", "")
                
                saved_keys = db.get_passkeys_by_rp(user['id'], rp_id, user['key'])
                if not saved_keys:
                    send_message({"error": "No passkeys found for this domain."})
                    continue
                    
                # Just use the first one for now
                pk_data = saved_keys[0]
                
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                
                authorized = messagebox.askyesno("VaultMate - Passkey", 
                                                 f"Use your Passkey to login to {rp_id}?\nClick Yes to authorize.", 
                                                 parent=root)
                root.destroy()
                
                if not authorized:
                    send_message({"error": "User cancelled passkey login"})
                    continue
                    
                # 1. Load Private Key
                private_key = serialization.load_pem_private_key(pk_data['private_key'], password=None)
                credential_id = bytes.fromhex(pk_data['credential_id'])
                
                # 2. Update Sign Count
                new_sign_count = pk_data['sign_count'] + 1
                db.update_passkey_sign_count(pk_data['id'], new_sign_count)
                
                # 3. ClientDataJSON
                client_data = json.dumps({
                    "type": "webauthn.get",
                    "challenge": challenge_b64,
                    "origin": msg.get("url").split('/')[0] + "//" + msg.get("url").split('/')[2],
                    "crossOrigin": False
                }).encode('utf-8')
                client_data_hash = hashlib.sha256(client_data).digest()
                
                # 4. AuthData
                rp_id_hash = hashlib.sha256(rp_id.encode('utf-8')).digest()
                flags = 0x05 # UP=1, UV=1
                auth_data = AuthenticatorData.create(rp_id_hash, flags, new_sign_count)
                
                # 5. Sign
                signature = private_key.sign(
                    auth_data + client_data_hash,
                    ec.ECDSA(SHA256())
                )
                
                def b64u(b):
                    return base64.urlsafe_b64encode(b).decode('ascii').rstrip('=')
                
                cred_response = {
                    "id": b64u(credential_id),
                    "rawId": {"__type": "ArrayBuffer", "data": b64u(credential_id)},
                    "response": {
                        "authenticatorData": {"__type": "ArrayBuffer", "data": b64u(auth_data)},
                        "clientDataJSON": {"__type": "ArrayBuffer", "data": b64u(client_data)},
                        "signature": {"__type": "ArrayBuffer", "data": b64u(signature)}
                    },
                    "type": "public-key"
                }
                
                if pk_data.get('user_handle'):
                    cred_response["response"]["userHandle"] = {"__type": "ArrayBuffer", "data": pk_data['user_handle']}
                
                send_message({"credential": cred_response})
            else:
                send_message({"error": "Unknown action"})
            
        except Exception as e:
            err_msg = f"Global error: {traceback.format_exc()}"
            log_error(err_msg)
            send_message({"error": str(e)})

if __name__ == '__main__':
    main()
