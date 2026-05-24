import sqlite3
import os
import bcrypt
from crypto_utils import derive_key, encrypt_data, decrypt_data

class Database:
    def __init__(self, db_path="vaultmate.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt BLOB NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            app_name TEXT NOT NULL,
            username TEXT,
            encrypted_password TEXT NOT NULL,
            encrypted_note TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS web_passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            web_url TEXT NOT NULL,
            website_name TEXT NOT NULL,
            username TEXT,
            encrypted_password TEXT NOT NULL,
            encrypted_note TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS passkeys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            rp_id TEXT NOT NULL,
            user_name TEXT,
            credential_id BLOB NOT NULL,
            public_key BLOB NOT NULL,
            private_key BLOB NOT NULL,
            sign_count INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        # Auto-migrate existing database tables
        try:
            cursor.execute("ALTER TABLE passkeys ADD COLUMN user_name TEXT")
        except Exception:
            pass # Column already exists
            
        try:
            cursor.execute("ALTER TABLE passkeys ADD COLUMN user_handle TEXT")
        except Exception:
            pass # Column already exists
        
        self.conn.commit()

    def create_user(self, username, password):
        cursor = self.conn.cursor()
        
        # Check if username exists
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return False, "Username already exists"
            
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        salt = os.urandom(16)
        
        try:
            cursor.execute('INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)',
                           (username, hashed_password, salt))
            self.conn.commit()
            return True, "Success"
        except sqlite3.IntegrityError:
            return False, "Database error"

    def login(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user:
            stored_hash = user['password_hash'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                # Derive the encryption key to return alongside the user dict
                key = derive_key(password, user['salt'])
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'key': key
                }
        return None

    def get_user_by_username(self, username):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, username FROM users WHERE username = ?', (username,))
        return dict(cursor.fetchone()) if cursor.fetchone() else None

    def add_app_password(self, user_id, app_name, username, password, note, key):
        try:
            encrypted_password = encrypt_data(password, key)
            encrypted_note = encrypt_data(note, key) if note else ""
            
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO app_passwords (user_id, app_name, username, encrypted_password, encrypted_note)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, app_name, username, encrypted_password, encrypted_note))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding app password: {e}")
            return False

    def add_web_password(self, user_id, web_url, website_name, username, password, note, key):
        try:
            encrypted_password = encrypt_data(password, key)
            encrypted_note = encrypt_data(note, key) if note else ""
            
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO web_passwords (user_id, web_url, website_name, username, encrypted_password, encrypted_note)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, web_url, website_name, username, encrypted_password, encrypted_note))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding web password: {e}")
            return False

    def update_web_password(self, pwd_id, user_id, url, website_name, username, password, notes, key):
        try:
            f = Fernet(key)
            encrypted_password = f.encrypt(password.encode()).decode()
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE web_passwords 
                    SET web_url=?, website_name=?, username=?, encrypted_password=?, notes=?
                    WHERE id=? AND user_id=?
                ''', (url, website_name, username, encrypted_password, notes, pwd_id, user_id))
            return True
        except Exception as e:
            print(f"Error updating web password: {e}")
            return False

    def get_app_passwords(self, user_id, key):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM app_passwords WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        
        passwords = []
        for row in rows:
            try:
                decrypted_password = decrypt_data(row['encrypted_password'], key)
                decrypted_note = decrypt_data(row['encrypted_note'], key) if row['encrypted_note'] else ""
                
                passwords.append({
                    'id': row['id'],
                    'app_name': row['app_name'],
                    'username': row['username'],
                    'password': decrypted_password,
                    'note': decrypted_note
                })
            except Exception as e:
                print(f"Failed to decrypt app password ID {row['id']}: {e}")
                
        return passwords

    def get_web_passwords(self, user_id, key):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM web_passwords WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        
        passwords = []
        for row in rows:
            try:
                decrypted_password = decrypt_data(row['encrypted_password'], key)
                decrypted_note = decrypt_data(row['encrypted_note'], key) if row['encrypted_note'] else ""
                
                passwords.append({
                    'id': row['id'],
                    'web_url': row['web_url'],
                    'website_name': row['website_name'],
                    'username': row['username'],
                    'password': decrypted_password,
                    'note': decrypted_note
                })
            except Exception as e:
                print(f"Failed to decrypt web password ID {row['id']}: {e}")
                
        return passwords

    def update_password_master(self, user_id, old_password, new_password, new_key):
        """Changes the master password. Requires re-encrypting all saved data."""
        # 1. Fetch current passwords using OLD key
        # 2. Re-encrypt with NEW key
        # 3. Update master password hash and salt
        pass # To be implemented if we want change password functionality. For now, leave it out for simplicity, or we can just implement it.

    def delete_app_password(self, password_id, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM app_passwords WHERE id = ? AND user_id = ?', (password_id, user_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting app password: {e}")
            return False

    def delete_web_password(self, password_id, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM web_passwords WHERE id = ? AND user_id = ?', (password_id, user_id))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting web password: {e}")
            return False

    def delete_user(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM app_passwords WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM web_passwords WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM passkeys WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def add_passkey(self, user_id, rp_id, user_name, credential_id, public_key, private_key, key, user_handle=None):
        try:
            encrypted_pub = encrypt_data(public_key.hex(), key)
            encrypted_priv = encrypt_data(private_key.hex(), key)
            
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO passkeys (user_id, rp_id, user_name, credential_id, public_key, private_key, sign_count, user_handle)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, rp_id, user_name, credential_id, encrypted_pub, encrypted_priv, 0, user_handle))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding passkey: {e}")
            return False

    def get_passkeys_by_rp(self, user_id, rp_id, key):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM passkeys WHERE user_id = ? AND rp_id = ?', (user_id, rp_id))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            try:
                decrypted_pub = bytes.fromhex(decrypt_data(row['public_key'], key))
                decrypted_priv = bytes.fromhex(decrypt_data(row['private_key'], key))
                
                results.append({
                    'id': row['id'],
                    'rp_id': row['rp_id'],
                    'credential_id': row['credential_id'],
                    'public_key': decrypted_pub,
                    'private_key': decrypted_priv,
                    'sign_count': row['sign_count'],
                    'user_handle': row['user_handle']
                })
            except Exception as e:
                print(f"Failed to decrypt passkey: {e}")
        return results

    def update_passkey_sign_count(self, passkey_id, new_count):
        try:
            cursor = self.conn.cursor()
            cursor.execute('UPDATE passkeys SET sign_count = ? WHERE id = ?', (new_count, passkey_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating sign count: {e}")
            return False

    def get_all_passkeys(self, user_id, key):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, rp_id, user_name FROM passkeys WHERE user_id = ?', (user_id,))
        rows = cursor.fetchall()
        
        # We only need the domain (rp_id) and id for the UI right now.
        # Decrypting private keys is unnecessary for displaying the list.
        results = []
        for row in rows:
            results.append({
                'id': row['id'],
                'rp_id': row['rp_id'],
                'user_name': row['user_name'] or 'unknown'
            })
        return results

    def delete_passkey(self, passkey_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM passkeys WHERE id = ?', (passkey_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting passkey: {e}")
            return False