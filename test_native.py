import json, struct, subprocess

msg = {"action": "passkey_create", "options": {"rp": {"id": "github.com"}, "user": {"name": "testuser"}, "challenge": {"data": "test"}}}
data = json.dumps(msg).encode('utf-8')
encoded = struct.pack('@I', len(data)) + data

p = subprocess.Popen(['python3', '/home/krishna/vaultmate-gui/Application/native_host.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate(input=encoded)
print("STDOUT:", out)
print("STDERR:", err.decode())
