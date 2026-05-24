import os
import json
import configparser

def get_chromium_profiles(local_state_path):
    profiles = []
    if not os.path.exists(local_state_path):
        return profiles
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            for folder, info in info_cache.items():
                name = info.get("name", folder)
                profiles.append(name)
    except Exception as e:
        print(f"Error parsing Chromium Local State at {local_state_path}: {e}")
    return profiles

def get_firefox_profiles(profiles_ini_path):
    profiles = []
    if not os.path.exists(profiles_ini_path):
        return profiles
    try:
        config = configparser.ConfigParser()
        config.read(profiles_ini_path)
        for section in config.sections():
            if section.lower().startswith("profile") or section.lower().startswith("install"):
                name = config[section].get("Name")
                if name and name not in profiles:
                    profiles.append(name)
    except Exception as e:
        print(f"Error parsing Firefox profiles.ini at {profiles_ini_path}: {e}")
    return profiles

def get_profiles_for_browser(browser_name):
    profiles = []
    home = os.path.expanduser("~")
    
    if browser_name == "Firefox":
        # Native Firefox
        profiles.extend(get_firefox_profiles(os.path.join(home, ".mozilla", "firefox", "profiles.ini")))
        # Fedora/some distros might use .config
        profiles.extend(get_firefox_profiles(os.path.join(home, ".config", "mozilla", "firefox", "profiles.ini")))
        # Flatpak Firefox
        profiles.extend(get_firefox_profiles(os.path.join(home, ".var", "app", "org.mozilla.firefox", ".mozilla", "firefox", "profiles.ini")))
    
    elif browser_name == "Chrome":
        profiles.extend(get_chromium_profiles(os.path.join(home, ".config", "google-chrome", "Local State")))
        profiles.extend(get_chromium_profiles(os.path.join(home, ".var", "app", "com.google.Chrome", "config", "google-chrome", "Local State")))
    
    elif browser_name == "Chromium":
        profiles.extend(get_chromium_profiles(os.path.join(home, ".config", "chromium", "Local State")))
        profiles.extend(get_chromium_profiles(os.path.join(home, ".var", "app", "org.chromium.Chromium", "config", "chromium", "Local State")))
        
    elif browser_name == "Brave":
        profiles.extend(get_chromium_profiles(os.path.join(home, ".config", "BraveSoftware", "Brave-Browser", "Local State")))
        profiles.extend(get_chromium_profiles(os.path.join(home, ".var", "app", "com.brave.Browser", "config", "BraveSoftware", "Brave-Browser", "Local State")))
        
    elif browser_name == "Edge":
        profiles.extend(get_chromium_profiles(os.path.join(home, ".config", "microsoft-edge", "Local State")))
        profiles.extend(get_chromium_profiles(os.path.join(home, ".var", "app", "com.microsoft.Edge", "config", "microsoft-edge", "Local State")))
    
    # Deduplicate and sort
    profiles = list(set(profiles))
    profiles.sort()
    
    # Always provide at least a Default option if nothing is found
    if not profiles:
        profiles = ["Default"]
        
    return profiles
