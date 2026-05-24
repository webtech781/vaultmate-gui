import os
import sys
import json
import platform
import stat
import shutil

HOST_NAME = "com.vaultmate.passkey"
FIREFOX_EXT_ID = "vaultmate@local.dev"

def get_browser_dirs(browser_name):
    os_name = platform.system()
    if os_name == "Windows":
        if browser_name == "Chrome":
            return rf"Software\Google\Chrome\NativeMessagingHosts\{HOST_NAME}"
        elif browser_name == "Edge":
            return rf"Software\Microsoft\Edge\NativeMessagingHosts\{HOST_NAME}"
        elif browser_name == "Firefox":
            return rf"Software\Mozilla\NativeMessagingHosts\{HOST_NAME}"
    elif os_name == "Darwin":
        if browser_name == "Chrome":
            return os.path.expanduser("~/Library/Application Support/Google/Chrome/NativeMessagingHosts")
        elif browser_name == "Edge":
            return os.path.expanduser("~/Library/Application Support/Microsoft Edge/NativeMessagingHosts")
        elif browser_name == "Firefox":
            return os.path.expanduser("~/Library/Application Support/Mozilla/NativeMessagingHosts")
    else: # Linux
        paths = []
        if browser_name == "Chrome":
            paths.append(os.path.expanduser("~/.config/google-chrome/NativeMessagingHosts"))
            paths.append(os.path.expanduser("~/.config/chromium/NativeMessagingHosts"))
            # Flatpak Chromium
            paths.append(os.path.expanduser("~/.var/app/org.chromium.Chromium/config/chromium/NativeMessagingHosts"))
        elif browser_name == "Edge":
            paths.append(os.path.expanduser("~/.config/microsoft-edge/NativeMessagingHosts"))
            paths.append(os.path.expanduser("~/.var/app/com.microsoft.Edge/config/microsoft-edge/NativeMessagingHosts"))
        elif browser_name == "Brave":
            paths.append(os.path.expanduser("~/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"))
            paths.append(os.path.expanduser("~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/NativeMessagingHosts"))
        elif browser_name == "Firefox":
            paths.append(os.path.expanduser("~/.mozilla/native-messaging-hosts"))
            # Flatpak Firefox
            paths.append(os.path.expanduser("~/.var/app/org.mozilla.firefox/.mozilla/native-messaging-hosts"))
        return paths

def install_for_browser(browser_name, extension_id=""):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    native_host_path = os.path.join(current_dir, "native_host.py")
    
    if not os.path.exists(native_host_path):
        return False, f"Could not find native_host.py at {native_host_path}"

    manifest = {
        "name": HOST_NAME,
        "description": "VaultMate Passkey Native Host",
        "path": native_host_path,
        "type": "stdio"
    }
    
    if browser_name == "Firefox":
        manifest["allowed_extensions"] = [FIREFOX_EXT_ID]
    else:
        manifest["allowed_origins"] = [f"chrome-extension://{extension_id}/" if extension_id else "chrome-extension://placeholder/"]

    os_name = platform.system()
    
    try:
        if os_name == "Windows":
            bat_path = os.path.join(current_dir, "native_host.bat")
            if not os.path.exists(bat_path):
                with open(bat_path, "w") as f:
                    f.write(f'@echo off\r\npython "{native_host_path}" %*')
            
            manifest["path"] = bat_path
            manifest_path = os.path.join(current_dir, f"{HOST_NAME}_{browser_name.lower()}.json")
            
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=4)
                
            import winreg
            key_path = get_browser_dirs(browser_name)
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(reg_key, "", 0, winreg.REG_SZ, manifest_path)
            winreg.CloseKey(reg_key)
            return True, f"Successfully connected to {browser_name}"

        else:
            st = os.stat(native_host_path)
            os.chmod(native_host_path, st.st_mode | stat.S_IEXEC)
            
            if os_name == "Linux":
                import subprocess
                flatpak_ids = {
                    "Firefox": "org.mozilla.firefox",
                    "Chrome": "com.google.Chrome",
                    "Chromium": "org.chromium.Chromium",
                    "Brave": "com.brave.Browser",
                    "Edge": "com.microsoft.Edge"
                }
                if browser_name in flatpak_ids:
                    app_id = flatpak_ids[browser_name]
                    # Grant permission for the Flatpak browser to execute the host wrapper script and read the directory
                    try:
                        subprocess.run(["flatpak", "override", "--user", "--talk-name=org.freedesktop.Flatpak", f"--filesystem={current_dir}", app_id], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                        
                sh_path = os.path.join(current_dir, "native_host.sh")
                # Prefer the venv Python so all packages (cryptography, etc.) are available
                venv_python = os.path.join(current_dir, ".venv", "bin", "python3")
                python_exe = venv_python if os.path.exists(venv_python) else sys.executable
                with open(sh_path, "w") as f:
                    f.write(f'''#!/bin/bash
# VaultMate Native Host Wrapper - uses venv Python with all required packages
VENV_PYTHON="{python_exe}"
NATIVE_HOST="{native_host_path}"
if [ -f /.flatpak-info ]; then
    exec flatpak-spawn --host "$VENV_PYTHON" "$NATIVE_HOST" "$@"
else
    exec "$VENV_PYTHON" "$NATIVE_HOST" "$@"
fi
''')
                os.chmod(sh_path, st.st_mode | stat.S_IEXEC)
                manifest["path"] = sh_path
            
            target_dirs = get_browser_dirs(browser_name)
            if not isinstance(target_dirs, list):
                target_dirs = [target_dirs]
                
            for target_dir in target_dirs:
                if not target_dir: continue
                os.makedirs(target_dir, exist_ok=True)
                with open(os.path.join(target_dir, f"{HOST_NAME}.json"), "w") as f:
                    json.dump(manifest, f, indent=4)
                
            return True, f"Successfully connected to {browser_name}"
            
    except Exception as e:
        return False, str(e)

def uninstall_for_browser(browser_name):
    os_name = platform.system()
    try:
        if os_name == "Windows":
            import winreg
            key_path = get_browser_dirs(browser_name)
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            return True, f"Disconnected {browser_name}"
        else:
            target_dirs = get_browser_dirs(browser_name)
            if not isinstance(target_dirs, list):
                target_dirs = [target_dirs]
            for target_dir in target_dirs:
                if not target_dir: continue
                target_file = os.path.join(target_dir, f"{HOST_NAME}.json")
                if os.path.exists(target_file):
                    os.remove(target_file)
            return True, f"Disconnected {browser_name}"
    except Exception as e:
        return False, str(e)

def is_installed_for_browser(browser_name):
    os_name = platform.system()
    if os_name == "Windows":
        try:
            import winreg
            key_path = get_browser_dirs(browser_name)
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.CloseKey(key)
            return True
        except:
            return False
    else:
        target_dirs = get_browser_dirs(browser_name)
        if not isinstance(target_dirs, list):
            target_dirs = [target_dirs]
        for target_dir in target_dirs:
            if not target_dir: continue
            if os.path.exists(os.path.join(target_dir, f"{HOST_NAME}.json")):
                return True
        return False

def get_installed_extension_details(browser_name):
    os_name = platform.system()
    if os_name == "Windows":
        try:
            import winreg
            key_path = get_browser_dirs(browser_name)
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
            manifest_path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                    if "allowed_origins" in manifest:
                        return manifest["allowed_origins"][0].replace("chrome-extension://", "").rstrip("/")
                    elif "allowed_extensions" in manifest:
                        return manifest["allowed_extensions"][0]
        except:
            pass
    else:
        target_dirs = get_browser_dirs(browser_name)
        if not isinstance(target_dirs, list):
            target_dirs = [target_dirs]
        for target_dir in target_dirs:
            if not target_dir: continue
            manifest_path = os.path.join(target_dir, f"{HOST_NAME}.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                        if "allowed_origins" in manifest:
                            return manifest["allowed_origins"][0].replace("chrome-extension://", "").rstrip("/")
                        elif "allowed_extensions" in manifest:
                            return manifest["allowed_extensions"][0]
                except:
                    pass
    return None

def install_manifest(extension_id=""):
    # Backwards compatibility, install for all
    a, msg1 = install_for_browser("Chrome", extension_id)
    b, msg2 = install_for_browser("Firefox")
    return a or b, msg1 + " " + msg2

def is_installed():
    return is_installed_for_browser("Firefox") or is_installed_for_browser("Chrome")
