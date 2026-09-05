import urllib.request
import json

try:
    req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode())
        print("Ollama is running! Models:", [m['name'] for m in data.get('models', [])])
except Exception as e:
    print("Ollama check result:", str(e))
