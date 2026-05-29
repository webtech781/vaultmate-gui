#!/usr/bin/env python3
import sys
import os
import glob

# Ensure virtual environment dependencies are discoverable by any interpreter/linter
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PATHS = glob.glob(os.path.join(SCRIPT_DIR, ".venv", "lib", "python*", "site-packages"))
for path in VENV_PATHS:
    if path not in sys.path:
        sys.path.insert(0, path)

import json
import traceback
import struct
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
from crypto_utils import get_from_keyring, decrypt_data

def choose_passkey_gui(saved_keys, rp_id):
    selected_key = [None]
    
    root = tk.Tk()
    root.overrideredirect(True) # Borderless window for polished flat design
    
    # Premium dark-mode styling matching the saved credentials popup
    bg_color = "#14151a"
    fg_color = "#f8fafc"
    accent_color = "#6366f1"
    panel_bg = "#1e1f26"
    border_color = "#2d2e36"
    
    root.configure(bg=bg_color, highlightbackground=border_color, highlightthickness=1)
    root.attributes('-topmost', True)
    
    width = 380
    height = 360
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Drag window handlers
    def start_drag(event):
        root._drag_x = event.x
        root._drag_y = event.y
        
    def drag(event):
        try:
            deltax = event.x - root._drag_x
            deltay = event.y - root._drag_y
            x = root.winfo_x() + deltax
            y = root.winfo_y() + deltay
            root.geometry(f"+{x}+{y}")
        except AttributeError:
            pass
            
    # Title bar (serving as custom drag handle)
    title_bar = tk.Frame(root, bg=bg_color, cursor="fleur", height=40)
    title_bar.pack(fill="x", side="top")
    title_bar.bind("<Button-1>", start_drag)
    title_bar.bind("<B1-Motion>", drag)
    
    logo_label = tk.Label(title_bar, text="🔐", font=("Segoe UI", 16), bg=bg_color, fg=fg_color)
    logo_label.pack(side="left", padx=(15, 8))
    logo_label.bind("<Button-1>", start_drag)
    logo_label.bind("<B1-Motion>", drag)
    
    title_label = tk.Label(title_bar, text="VaultMate", font=("Segoe UI", 12, "bold"), bg=bg_color, fg=fg_color)
    title_label.pack(side="left")
    title_label.bind("<Button-1>", start_drag)
    title_label.bind("<B1-Motion>", drag)
    
    def on_cancel():
        selected_key[0] = None
        root.destroy()
        
    # Polished Close [X] button in header
    close_btn = tk.Label(title_bar, text="✕", font=("Segoe UI", 12), bg=bg_color, fg="#8a8b8f", cursor="hand2")
    close_btn.pack(side="right", padx=15)
    close_btn.bind("<Button-1>", lambda e: on_cancel())
    close_btn.bind("<Enter>", lambda e: close_btn.configure(fg="#ffffff"))
    close_btn.bind("<Leave>", lambda e: close_btn.configure(fg="#8a8b8f"))
    
    # Subtitle
    subtitle_label = tk.Label(root, text=f"Choose an account to login to {rp_id}:", 
                              font=("Segoe UI", 10), justify="left", bg=bg_color, fg="#94a3b8")
    subtitle_label.pack(fill="x", padx=20, pady=(10, 10))
    
    # Listbox Frame
    list_frame = tk.Frame(root, bg=panel_bg, bd=1, relief="flat", highlightbackground=border_color, highlightthickness=1)
    list_frame.pack(fill="both", expand=True, padx=20, pady=5)
    
    listbox = tk.Listbox(list_frame, bg=panel_bg, fg=fg_color, selectbackground=accent_color, 
                         selectforeground=fg_color, bd=0, highlightthickness=0, 
                         font=("Segoe UI", 11), activestyle="none")
    listbox.pack(fill="both", expand=True, padx=5, pady=5)
    
    for idx, key in enumerate(saved_keys):
        display_name = key.get('user_name') or key.get('user_handle') or f"Account {idx + 1}"
        if isinstance(display_name, bytes):
            try:
                display_name = display_name.decode('utf-8')
            except Exception:
                display_name = display_name.hex()[:10] + "..."
        listbox.insert(tk.END, f"  👤  {display_name}")
    
    listbox.select_set(0)
    
    def on_select():
        try:
            sel_idx = listbox.curselection()[0]
            selected_key[0] = saved_keys[sel_idx]
            root.destroy()
        except IndexError:
            pass
        
    listbox.bind("<Double-1>", lambda event: on_select())
    
    # Buttons Frame
    btn_frame = tk.Frame(root, bg=bg_color, pady=15)
    btn_frame.pack(fill="x", padx=20)
    
    cancel_btn = tk.Button(btn_frame, text="Cancel", command=on_cancel, 
                           bg="#2e303e", fg="#cbd5e1", font=("Segoe UI", 10, "bold"),
                           activebackground="#3e4052", activeforeground=fg_color,
                           bd=0, cursor="hand2", padx=15, pady=6)
    cancel_btn.pack(side="left")
    
    select_btn = tk.Button(btn_frame, text="Use Passkey", command=on_select, 
                           bg=accent_color, fg=fg_color, font=("Segoe UI", 10, "bold"),
                           activebackground="#4f46e5", activeforeground=fg_color,
                           bd=0, cursor="hand2", padx=15, pady=6)
    select_btn.pack(side="right")
    
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()
    
    return selected_key[0]

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
            
            if action == "ping":
                auth = get_active_user()
                if auth:
                    db, user = auth
                    send_message({"status": "success", "unlocked": True, "username": user['username']})
                else:
                    send_message({"status": "success", "unlocked": False})
                continue
                
            auth = get_active_user()
            if not auth:
                send_message({"error": "VaultMate is locked or not configured for OS Auto-Login."})
                continue
                
            db, user = auth
            
            if action == "autofill_request":
                url = msg.get("url", "").lower()
                passwords = db.get_web_passwords(user['id'], user['key'])
                
                matches = []
                # 1. Fetch matching passwords
                for p in passwords:
                    saved_domain = p['web_url'].replace('https://','').replace('http://','').split('/')[0].lower()
                    if saved_domain in url:
                        matches.append({
                            "username": p['username'],
                            "password": p['password'],
                            "type": "password"
                        })
                
                # 2. Fetch matching passkeys
                current_domain = url.replace('https://','').replace('http://','').split('/')[0].lower()
                if current_domain.startswith("www."):
                    current_domain = current_domain[4:]
                    
                passkeys = db.get_passkeys_by_rp(user['id'], current_domain, user['key'])
                for pk in passkeys:
                    display_name = pk.get('user_name') or pk.get('user_handle') or "Saved Passkey"
                    if isinstance(display_name, bytes):
                        try:
                            display_name = display_name.decode('utf-8')
                        except Exception:
                            display_name = display_name.hex()[:10] + "..."
                    matches.append({
                        "username": display_name,
                        "type": "passkey",
                        "id": pk['id']
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
                
            elif action == "auto_save_confirm":
                url = msg.get("url")
                name = msg.get("name")
                username = msg.get("username")
                password = msg.get("password")
                
                existing = db.get_web_passwords(user['id'], user['key'])
                exists = False
                update_pid = None
                
                for p in existing:
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
                    db.add_web_password(user['id'], url, name, username, password, "", user['key'])
                elif update_pid:
                    db.update_web_password(update_pid, user['id'], url, name, username, password, "", user['key'])
                
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
                    
                # Present choice prompt if multiple passkeys are saved
                if len(saved_keys) > 1:
                    pk_data = choose_passkey_gui(saved_keys, rp_id)
                    if not pk_data:
                        send_message({"error": "User cancelled passkey selection"})
                        continue
                    authorized = True # Explicitly authorized via the select window
                else:
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

            elif action == "passkey_get_by_id":
                passkey_id = msg.get("passkey_id")
                options = msg.get("options", {}).get("publicKey", {})
                rp_id = options.get("rpId", msg.get("url", "//unknown").split('/')[2])
                challenge_b64 = options.get("challenge", {}).get("data", "")
                
                cursor = db.conn.cursor()
                cursor.execute('SELECT * FROM passkeys WHERE id = ? AND user_id = ?', (passkey_id, user['id']))
                row = cursor.fetchone()
                if not row:
                    send_message({"error": "Passkey not found"})
                    continue
                    
                decrypted_priv = bytes.fromhex(decrypt_data(row['private_key'], user['key']))
                pk_data = {
                    'private_key': decrypted_priv,
                    'credential_id': row['credential_id'],
                    'sign_count': row['sign_count'],
                    'user_handle': row['user_handle'],
                    'id': row['id']
                }
                
                private_key = serialization.load_pem_private_key(pk_data['private_key'], password=None)
                credential_id = bytes.fromhex(pk_data['credential_id'])
                
                new_sign_count = pk_data['sign_count'] + 1
                db.update_passkey_sign_count(pk_data['id'], new_sign_count)
                
                client_data = json.dumps({
                    "type": "webauthn.get",
                    "challenge": challenge_b64,
                    "origin": msg.get("url").split('/')[0] + "//" + msg.get("url").split('/')[2],
                    "crossOrigin": False
                }).encode('utf-8')
                client_data_hash = hashlib.sha256(client_data).digest()
                
                rp_id_hash = hashlib.sha256(rp_id.encode('utf-8')).digest()
                flags = 0x05 # UP=1, UV=1
                auth_data = AuthenticatorData.create(rp_id_hash, flags, new_sign_count)
                
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
