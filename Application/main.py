import customtkinter as ctk
from tkinter import messagebox, filedialog
from database import Database
from crypto_utils import save_to_keyring, get_from_keyring, delete_from_keyring, derive_key
from extension_installer import is_installed, is_installed_for_browser, install_for_browser, uninstall_for_browser, get_installed_extension_details
import json
import os

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "vaultmate_config.json"

class PasswordManager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VaultMate - Password Manager")
        self.geometry("900x650")
        
        self.db = Database()
        self.current_user = None
        
        # Configure grid system
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Add a global theme toggle button (hidden on dashboard, shown elsewhere)
        self.theme_btn = ctk.CTkButton(self, text="🌓 Toggle Theme", command=self.toggle_theme, width=120, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
        self.theme_btn.place(relx=0.98, rely=0.02, anchor="ne")
        
        self.attempt_auto_login()

    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

    def get_last_username(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    return config.get("last_username")
            except Exception:
                pass
        return None

    def save_last_username(self, username):
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
            except Exception:
                pass
                
        config["last_username"] = username
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception:
            pass

    def get_browser_profile(self, browser_name):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    profiles = config.get("browser_profiles", {})
                    return profiles.get(browser_name)
            except Exception:
                pass
        return None

    def save_browser_profile(self, browser_name, profile_name):
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
            except Exception:
                pass
        
        if "browser_profiles" not in config:
            config["browser_profiles"] = {}
            
        config["browser_profiles"][browser_name] = profile_name
        
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception:
            pass

    def delete_browser_profile(self, browser_name):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                
                if "browser_profiles" in config and browser_name in config["browser_profiles"]:
                    del config["browser_profiles"][browser_name]
                    with open(CONFIG_FILE, "w") as f:
                        json.dump(config, f)
            except Exception:
                pass

    def attempt_auto_login(self):
        username = self.get_last_username()
        if username:
            try:
                # This call might trigger the OS biometric/PIN prompt
                password = get_from_keyring(username)
                if password:
                    user = self.db.login(username, password)
                    if user:
                        self.current_user = user
                        self.show_main_dashboard()
                        return
            except Exception as e:
                print(f"Keyring auto-login failed: {e}")
        
        self.show_login_page()

    def clear_frame(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        self.main_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=0)
        self.main_frame.grid_columnconfigure((0, 1, 2, 3), weight=0)

    def show_login_page(self):
        self.clear_frame()
        self.theme_btn.place(relx=0.98, rely=0.02, anchor="ne") # Show global toggle
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(self.main_frame, text="VaultMate", font=ctk.CTkFont(family="Helvetica", size=36, weight="bold"))
        title.grid(row=0, column=0, pady=(60, 20))
        
        login_frame = ctk.CTkFrame(self.main_frame, width=400, corner_radius=12)
        login_frame.grid(row=1, column=0, pady=20)
        login_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(login_frame, text="Login to your Vault", font=ctk.CTkFont(family="Helvetica", size=18)).grid(row=0, column=0, pady=(30, 20))
        
        self.username_entry = ctk.CTkEntry(login_frame, placeholder_text="Username", width=260, height=40)
        self.username_entry.grid(row=1, column=0, pady=(0, 15))
        
        last_user = self.get_last_username()
        if last_user:
            self.username_entry.insert(0, last_user)
        
        self.password_entry = ctk.CTkEntry(login_frame, placeholder_text="Master Password", show="*", width=260, height=40)
        self.password_entry.grid(row=2, column=0, pady=(0, 15))
        
        self.remember_var = ctk.BooleanVar(value=True)
        remember_cb = ctk.CTkCheckBox(login_frame, text="Remember Me (OS Biometrics/PIN)", variable=self.remember_var)
        remember_cb.grid(row=3, column=0, pady=(0, 20))
        
        login_btn = ctk.CTkButton(login_frame, text="Login", command=self.login, width=260, height=40, fg_color="#007AFF", hover_color="#0056B3", corner_radius=8, font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        login_btn.grid(row=4, column=0, pady=(0, 10))
        
        create_btn = ctk.CTkButton(login_frame, text="Create Local Account", command=self.show_create_account_page, fg_color="transparent", border_width=1, border_color="#007AFF", text_color=("gray10", "#DCE4EE"), width=260, height=40, corner_radius=8)
        create_btn.grid(row=5, column=0, pady=(0, 30))

    def show_create_account_page(self):
        self.clear_frame()
        self.theme_btn.place(relx=0.98, rely=0.02, anchor="ne")
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(self.main_frame, text="Create Vault", font=ctk.CTkFont(family="Helvetica", size=36, weight="bold"))
        title.grid(row=0, column=0, pady=(60, 20))
        
        reg_frame = ctk.CTkFrame(self.main_frame, width=400, corner_radius=12)
        reg_frame.grid(row=1, column=0, pady=20)
        reg_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(reg_frame, text="Set up your Master Password", font=ctk.CTkFont(family="Helvetica", size=18)).grid(row=0, column=0, pady=(30, 20))
        
        self.new_user_entry = ctk.CTkEntry(reg_frame, placeholder_text="Username", width=260, height=40)
        self.new_user_entry.grid(row=1, column=0, pady=(0, 15))
        
        self.new_pass_entry = ctk.CTkEntry(reg_frame, placeholder_text="Master Password", show="*", width=260, height=40)
        self.new_pass_entry.grid(row=2, column=0, pady=(0, 15))
        
        self.confirm_pass_entry = ctk.CTkEntry(reg_frame, placeholder_text="Confirm Master Password", show="*", width=260, height=40)
        self.confirm_pass_entry.grid(row=3, column=0, pady=(0, 15))
        
        self.reg_remember_var = ctk.BooleanVar(value=True)
        reg_remember_cb = ctk.CTkCheckBox(reg_frame, text="Enable OS Biometrics/PIN login", variable=self.reg_remember_var)
        reg_remember_cb.grid(row=4, column=0, pady=(0, 20))
        
        create_btn = ctk.CTkButton(reg_frame, text="Create Account", command=self.create_account, width=260, height=40, fg_color="#007AFF", hover_color="#0056B3", corner_radius=8, font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        create_btn.grid(row=5, column=0, pady=(0, 10))
        
        back_btn = ctk.CTkButton(reg_frame, text="Back to Login", command=self.show_login_page, fg_color="transparent", border_width=1, border_color="#007AFF", text_color=("gray10", "#DCE4EE"), width=260, height=40, corner_radius=8)
        back_btn.grid(row=6, column=0, pady=(0, 30))

    def create_account(self):
        username = self.new_user_entry.get().strip()
        password = self.new_pass_entry.get()
        confirm = self.confirm_pass_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "All fields are required")
            return
            
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return
            
        success, msg = self.db.create_user(username, password)
        if success:
            self.save_last_username(username)
            if self.reg_remember_var.get():
                try:
                    save_to_keyring(username, password)
                except Exception as e:
                    print(f"Failed to save to keyring: {e}")
                    
            messagebox.showinfo("Success", "Account created successfully. You can now login.")
            self.show_login_page()
        else:
            messagebox.showerror("Error", msg)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        user = self.db.login(username, password)
        if user:
            self.current_user = user
            self.save_last_username(username)
            if self.remember_var.get():
                try:
                    save_to_keyring(username, password)
                except Exception as e:
                    print(f"Failed to save to keyring: {e}")
            else:
                delete_from_keyring(username)
                
            self.show_main_dashboard()
        else:
            messagebox.showerror("Error", "Invalid username or password")

    def logout(self):
        if self.current_user:
            delete_from_keyring(self.current_user['username'])
        self.current_user = None
        self.save_last_username("") # Clear auto-login
        self.show_login_page()

    def show_main_dashboard(self):
        self.clear_frame()
        self.theme_btn.place_forget() # Hide the global floating theme button since we move it to the sidebar
        
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=0) # Sidebar
        self.main_frame.grid_columnconfigure(1, weight=1) # Main Content
        
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=220, corner_radius=0, fg_color=("gray90", "gray13"))
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)
        
        logo_label = ctk.CTkLabel(self.sidebar_frame, text="VaultMate", font=ctk.CTkFont(family="Helvetica", size=26, weight="bold"))
        logo_label.grid(row=0, column=0, padx=20, pady=(30, 5), sticky="w")
        
        welcome_lbl = ctk.CTkLabel(self.sidebar_frame, text=f"Hi, {self.current_user['username']}!", font=ctk.CTkFont(family="Helvetica", size=14), text_color="gray")
        welcome_lbl.grid(row=1, column=0, padx=20, pady=(0, 30), sticky="w")
        
        add_app_btn = ctk.CTkButton(self.sidebar_frame, text="➕ App Password", command=self.show_add_app_password_page, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        add_app_btn.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        add_web_btn = ctk.CTkButton(self.sidebar_frame, text="➕ Web Password", command=self.show_add_web_password_page, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        add_web_btn.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        ext_status = "✅ Browser Integrations"
        add_ext_btn = ctk.CTkButton(self.sidebar_frame, text=ext_status, command=self.show_browser_integrations_page, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        add_ext_btn.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        
        export_btn = ctk.CTkButton(self.sidebar_frame, text="🔒 Export Backup", command=self.export_backup, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        export_btn.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        import_btn = ctk.CTkButton(self.sidebar_frame, text="🔓 Import Backup", command=self.import_backup, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        import_btn.grid(row=6, column=0, padx=20, pady=5, sticky="ew")
        
        self.theme_btn_sidebar = ctk.CTkButton(self.sidebar_frame, text="🌓 Toggle Theme", command=self.toggle_theme, fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray75", "gray25"), anchor="w")
        self.theme_btn_sidebar.grid(row=8, column=0, padx=20, pady=(10, 5), sticky="ew")
        
        logout_btn = ctk.CTkButton(self.sidebar_frame, text="🚪 Logout", command=self.logout, fg_color="#E74C3C", hover_color="#C0392B", text_color="white", anchor="w")
        logout_btn.grid(row=9, column=0, padx=20, pady=(5, 20), sticky="ew")
        
        # --- Main Content ---
        self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.content_frame.grid_rowconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_lbl = ctk.CTkLabel(header_frame, text="My Vault", font=ctk.CTkFont(family="Helvetica", size=32, weight="bold"))
        title_lbl.grid(row=0, column=0, sticky="w")
        
        refresh_btn = ctk.CTkButton(header_frame, text="🔄 Refresh", command=self.load_passwords_view, width=100, fg_color="#007AFF", hover_color="#0056B3")
        refresh_btn.grid(row=0, column=1, sticky="e")
        
        self.passwords_frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        self.passwords_frame.grid(row=1, column=0, sticky="nsew")
        self.passwords_frame.grid_columnconfigure(0, weight=1)
        
        self.load_passwords_view()

    def load_passwords_view(self):
        # Clear existing
        for w in self.passwords_frame.winfo_children():
            w.destroy()
            
        app_passwords = self.db.get_app_passwords(self.current_user['id'], self.current_user['key'])
        web_passwords = self.db.get_web_passwords(self.current_user['id'], self.current_user['key'])
        passkeys = self.db.get_all_passkeys(self.current_user['id'], self.current_user['key'])
        
        row_idx = 0
        
        # Section: Web Passwords
        if web_passwords:
            ctk.CTkLabel(self.passwords_frame, text="Web Passwords", font=ctk.CTkFont(size=18, weight="bold")).grid(row=row_idx, column=0, sticky="w", pady=(10, 5), padx=10)
            row_idx += 1
            for p in web_passwords:
                self.create_password_card(self.passwords_frame, p, is_web=True).grid(row=row_idx, column=0, sticky="ew", pady=5, padx=10)
                row_idx += 1
                
        # Section: App Passwords
        if app_passwords:
            ctk.CTkLabel(self.passwords_frame, text="App Passwords", font=ctk.CTkFont(size=18, weight="bold")).grid(row=row_idx, column=0, sticky="w", pady=(20, 5), padx=10)
            row_idx += 1
            for p in app_passwords:
                self.create_password_card(self.passwords_frame, p, is_web=False).grid(row=row_idx, column=0, sticky="ew", pady=5, padx=10)
                row_idx += 1
                
        # Section: Passkeys
        if passkeys:
            ctk.CTkLabel(self.passwords_frame, text="Passkeys", font=ctk.CTkFont(size=18, weight="bold")).grid(row=row_idx, column=0, sticky="w", pady=(20, 5), padx=10)
            row_idx += 1
            for pk in passkeys:
                self.create_passkey_card(self.passwords_frame, pk).grid(row=row_idx, column=0, sticky="ew", pady=5, padx=10)
                row_idx += 1

        if not app_passwords and not web_passwords and not passkeys:
            ctk.CTkLabel(self.passwords_frame, text="No credentials saved yet.", text_color="gray").grid(row=row_idx, column=0, pady=40)

    def create_passkey_card(self, parent, data):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=("white", "gray17"))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)
        
        domain = data['rp_id']
        username = data.get('user_name', 'unknown')
        pk_id = data['id']
        
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        ctk.CTkLabel(info_frame, text=domain, font=ctk.CTkFont(family="Helvetica", size=18, weight="bold"), wraplength=350, justify="left").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(info_frame, text=username, font=ctk.CTkFont(size=14), text_color="gray").grid(row=1, column=0, sticky="w")
        ctk.CTkLabel(info_frame, text="WebAuthn Passkey (Passwordless)", font=ctk.CTkFont(size=12), text_color="#10A37F").grid(row=2, column=0, sticky="w", pady=(2, 0))
        
        pass_frame = ctk.CTkFrame(card, fg_color="transparent")
        pass_frame.grid(row=0, column=1, sticky="e", padx=20, pady=15)
        
        def delete_pk():
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete the passkey for {domain}?"):
                self.db.delete_passkey(pk_id)
                self.load_passwords_view()
                
        delete_btn = ctk.CTkButton(pass_frame, text="Delete", width=60, fg_color="#E74C3C", hover_color="#C0392B", corner_radius=6, command=delete_pk)
        delete_btn.grid(row=0, column=0, padx=(0, 10))
        
        return card

    def create_password_card(self, parent, data, is_web=False):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=("white", "gray17"))
        card.grid_columnconfigure(0, weight=1) # Let the text area take up space
        card.grid_columnconfigure(1, weight=0) # Lock the buttons area
        
        title = data['website_name'] if is_web else data['app_name']
        subtitle = data['web_url'] if is_web else ""
        username = data['username']
        password = data['password']
        pid = data['id']
        
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        # Add wraplength so long titles don't push buttons off the screen
        ctk.CTkLabel(info_frame, text=title, font=ctk.CTkFont(family="Helvetica", size=18, weight="bold"), wraplength=350, justify="left").grid(row=0, column=0, sticky="w")
        if subtitle:
            ctk.CTkLabel(info_frame, text=subtitle, font=ctk.CTkFont(size=12), text_color="gray", wraplength=350, justify="left").grid(row=1, column=0, sticky="w")
        ctk.CTkLabel(info_frame, text=f"{username}").grid(row=2, column=0, sticky="w", pady=(5,0))
        
        pass_frame = ctk.CTkFrame(card, fg_color="transparent")
        pass_frame.grid(row=0, column=1, sticky="e", padx=20, pady=15)
        
        pass_entry = ctk.CTkEntry(pass_frame, width=140, show="*", border_width=1, corner_radius=6)
        pass_entry.insert(0, password)
        pass_entry.configure(state="readonly")
        pass_entry.grid(row=0, column=0, padx=(0, 10))
        
        def toggle_view():
            if pass_entry.cget("show") == "*":
                pass_entry.configure(show="")
                view_btn.configure(text="Hide")
            else:
                pass_entry.configure(show="*")
                view_btn.configure(text="View")
                
        def copy_pass():
            self.clipboard_clear()
            self.clipboard_append(password)
            messagebox.showinfo("Copied", "Password copied to clipboard")
            
        def delete_pass():
            if messagebox.askyesno("Confirm", "Are you sure you want to delete this password?"):
                if is_web:
                    self.db.delete_web_password(pid, self.current_user['id'])
                else:
                    self.db.delete_app_password(pid, self.current_user['id'])
                self.load_passwords_view()
        
        view_btn = ctk.CTkButton(pass_frame, text="View", width=60, fg_color="transparent", text_color=("gray10", "gray90"), border_width=1, corner_radius=6, command=toggle_view)
        view_btn.grid(row=0, column=1, padx=(0, 10))
        
        copy_btn = ctk.CTkButton(pass_frame, text="Copy", width=60, fg_color="#007AFF", hover_color="#0056B3", corner_radius=6, command=copy_pass)
        copy_btn.grid(row=0, column=2, padx=(0, 10))
        
        del_btn = ctk.CTkButton(pass_frame, text="Delete", width=60, fg_color="transparent", text_color="#E74C3C", hover_color="#FDEDEC", border_width=1, border_color="#E74C3C", corner_radius=6, command=delete_pass)
        del_btn.grid(row=0, column=3)
        
        return card

    def show_add_app_password_page(self):
        self.clear_frame()
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkButton(self.main_frame, text="← Back", width=80, command=self.show_main_dashboard).grid(row=0, column=0, sticky="w", padx=20, pady=20)
        
        title = ctk.CTkLabel(self.main_frame, text="Add App Password", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=1, column=0, pady=(0, 20))
        
        form_frame = ctk.CTkFrame(self.main_frame, width=400)
        form_frame.grid(row=2, column=0, pady=10)
        form_frame.grid_columnconfigure(0, weight=1)
        
        self.app_name_entry = ctk.CTkEntry(form_frame, placeholder_text="App Name (e.g. Steam)", width=300)
        self.app_name_entry.grid(row=0, column=0, pady=(20, 10), padx=20)
        
        self.app_user_entry = ctk.CTkEntry(form_frame, placeholder_text="Username / Email", width=300)
        self.app_user_entry.grid(row=1, column=0, pady=10, padx=20)
        
        self.app_pass_entry = ctk.CTkEntry(form_frame, placeholder_text="Password", show="*", width=300)
        self.app_pass_entry.grid(row=2, column=0, pady=10, padx=20)
        
        self.app_note_entry = ctk.CTkEntry(form_frame, placeholder_text="Note (Optional)", width=300)
        self.app_note_entry.grid(row=3, column=0, pady=10, padx=20)
        
        save_btn = ctk.CTkButton(form_frame, text="Save Password", command=self.save_app_password, width=300)
        save_btn.grid(row=4, column=0, pady=(10, 20), padx=20)

    def show_add_web_password_page(self):
        self.clear_frame()
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkButton(self.main_frame, text="← Back", width=80, command=self.show_main_dashboard).grid(row=0, column=0, sticky="w", padx=20, pady=20)
        
        title = ctk.CTkLabel(self.main_frame, text="Add Web Password", font=ctk.CTkFont(size=24, weight="bold"))
        title.grid(row=1, column=0, pady=(0, 20))
        
        form_frame = ctk.CTkFrame(self.main_frame, width=400)
        form_frame.grid(row=2, column=0, pady=10)
        form_frame.grid_columnconfigure(0, weight=1)
        
        self.web_url_entry = ctk.CTkEntry(form_frame, placeholder_text="Website URL (e.g. https://github.com)", width=300)
        self.web_url_entry.grid(row=0, column=0, pady=(20, 10), padx=20)
        
        self.web_name_entry = ctk.CTkEntry(form_frame, placeholder_text="Website Name (e.g. GitHub)", width=300)
        self.web_name_entry.grid(row=1, column=0, pady=10, padx=20)
        
        self.web_user_entry = ctk.CTkEntry(form_frame, placeholder_text="Username / Email", width=300)
        self.web_user_entry.grid(row=2, column=0, pady=10, padx=20)
        
        self.web_pass_entry = ctk.CTkEntry(form_frame, placeholder_text="Password", show="*", width=300)
        self.web_pass_entry.grid(row=3, column=0, pady=10, padx=20)
        
        self.web_note_entry = ctk.CTkEntry(form_frame, placeholder_text="Note (Optional)", width=300)
        self.web_note_entry.grid(row=4, column=0, pady=10, padx=20)
        
        save_btn = ctk.CTkButton(form_frame, text="Save Password", command=self.save_web_password, width=300)
        save_btn.grid(row=5, column=0, pady=(10, 20), padx=20)

    def save_app_password(self):
        app_name = self.app_name_entry.get().strip()
        username = self.app_user_entry.get().strip()
        password = self.app_pass_entry.get()
        note = self.app_note_entry.get().strip()
        
        if not app_name or not username or not password:
            messagebox.showerror("Error", "App Name, Username and Password are required")
            return
            
        success = self.db.add_app_password(self.current_user['id'], app_name, username, password, note, self.current_user['key'])
        if success:
            messagebox.showinfo("Success", "Password saved successfully!")
            self.show_main_dashboard()
        else:
            messagebox.showerror("Error", "Failed to save password")

    def save_web_password(self):
        url = self.web_url_entry.get().strip()
        name = self.web_name_entry.get().strip()
        username = self.web_user_entry.get().strip()
        password = self.web_pass_entry.get()
        note = self.web_note_entry.get().strip()
        
        if not url or not name or not username or not password:
            messagebox.showerror("Error", "URL, Name, Username and Password are required")
            return
            
        success = self.db.add_web_password(self.current_user['id'], url, name, username, password, note, self.current_user['key'])
        if success:
            messagebox.showinfo("Success", "Password saved successfully!")
            self.show_main_dashboard()
        else:
            messagebox.showerror("Error", "Failed to save password")

    def show_browser_integrations_page(self):
        self.clear_frame()
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkButton(self.main_frame, text="← Back", width=80, command=self.show_main_dashboard).grid(row=0, column=0, sticky="w", padx=20, pady=20)
        
        browsers = ["Firefox", "Chrome", "Edge"]
        connected_count = sum(1 for b in browsers if is_installed_for_browser(b))
        
        title_text = f"Browser Integrations ({connected_count} Connected)" if connected_count > 0 else "Browser Integrations"
        title = ctk.CTkLabel(self.main_frame, text=title_text, font=ctk.CTkFont(family="Helvetica", size=32, weight="bold"))
        title.grid(row=1, column=0, pady=(0, 20))
        
        row_idx = 2
        for b in browsers:
            frame = ctk.CTkFrame(self.main_frame, width=500, corner_radius=12)
            frame.grid(row=row_idx, column=0, pady=10, padx=20)
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_columnconfigure(1, weight=0)
            
            is_conn = is_installed_for_browser(b)
            
            lbl = ctk.CTkLabel(frame, text=f"{b} Browser", font=ctk.CTkFont(family="Helvetica", size=18, weight="bold"))
            lbl.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5) if is_conn else 20)
            
            if is_conn:
                profile_name = self.get_browser_profile(b)
                if profile_name:
                    sub_text = f"Profile: {profile_name}"
                else:
                    ext_id = get_installed_extension_details(b)
                    sub_text = f"ID: {ext_id}" if ext_id else "Connected"
                    
                sub_lbl = ctk.CTkLabel(frame, text=sub_text, font=ctk.CTkFont(size=12), text_color="#10A37F")
                sub_lbl.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
            
            def make_connect_cmd(browser=b):
                def cmd():
                    if browser == "Firefox":
                        success, msg = install_for_browser(browser)
                    else:
                        ext_id = ctk.CTkInputDialog(text=f"Enter {browser} Extension ID (from extensions page):", title="Connect").get_input()
                        if not ext_id: return
                        success, msg = install_for_browser(browser, ext_id)
                        
                    if success:
                        profile_name = ctk.CTkInputDialog(text=f"Enter a Profile Name for this {browser} connection\n(e.g. Work, Personal):", title="Profile Name").get_input()
                        if profile_name:
                            self.save_browser_profile(browser, profile_name)
                        messagebox.showinfo("Success", msg)
                    else:
                        messagebox.showerror("Error", msg)
                    self.show_browser_integrations_page()
                return cmd
                
            def make_disconnect_cmd(browser=b):
                def cmd():
                    success, msg = uninstall_for_browser(browser)
                    self.delete_browser_profile(browser)
                    self.show_browser_integrations_page()
                return cmd
                
            if is_conn:
                btn = ctk.CTkButton(frame, text="Disconnect", command=make_disconnect_cmd(), fg_color="transparent", text_color="#E74C3C", border_width=1, border_color="#E74C3C", hover_color="#FDEDEC", width=120, corner_radius=8)
                btn.grid(row=0, column=1, rowspan=2 if is_conn else 1, sticky="e", padx=20, pady=20)
            else:
                btn = ctk.CTkButton(frame, text="Connect", command=make_connect_cmd(), fg_color="#007AFF", hover_color="#0056B3", width=120, corner_radius=8)
                btn.grid(row=0, column=1, sticky="e", padx=20, pady=20)
                
            row_idx += 1

    def export_backup(self):
        password = ctk.CTkInputDialog(text="Enter a strong Backup Password:", title="Export Backup").get_input()
        if not password:
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".vaultmate_backup", filetypes=[("VaultMate Backup", "*.vaultmate_backup")])
        if not file_path:
            return
            
        try:
            salt = os.urandom(16)
            key = derive_key(password, salt)
            from cryptography.fernet import Fernet
            f = Fernet(key)
            
            with open("vaultmate.db", "rb") as db_file:
                db_data = db_file.read()
                
            encrypted_data = f.encrypt(db_data)
            
            with open(file_path, "wb") as backup_file:
                backup_file.write(salt + encrypted_data)
                
            messagebox.showinfo("Success", "Highly encrypted backup exported successfully!\nYou can safely save this file to Google Drive or Dropbox.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export backup: {e}")

    def import_backup(self):
        if not messagebox.askyesno("Warning", "Importing a backup will OVERWRITE your current vault. Do you want to continue?"):
            return
            
        file_path = filedialog.askopenfilename(filetypes=[("VaultMate Backup", "*.vaultmate_backup")])
        if not file_path:
            return
            
        password = ctk.CTkInputDialog(text="Enter the Backup Password:", title="Import Backup").get_input()
        if not password:
            return
            
        try:
            with open(file_path, "rb") as backup_file:
                content = backup_file.read()
                
            if len(content) < 16:
                raise ValueError("Invalid backup file")
                
            salt = content[:16]
            encrypted_data = content[16:]
            
            key = derive_key(password, salt)
            from cryptography.fernet import Fernet
            f = Fernet(key)
            
            decrypted_data = f.decrypt(encrypted_data)
            
            self.db.conn.close()
            
            with open("vaultmate.db", "wb") as db_file:
                db_file.write(decrypted_data)
                
            messagebox.showinfo("Success", "Backup restored successfully! The application will now close. Please restart it.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import backup. Incorrect password or corrupted file.")
            self.db = Database()

if __name__ == "__main__":
    app = PasswordManager()
    app.mainloop()