
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
if not key:
    print("Error: OPENROUTER_API_KEY not found in environment.")
    exit(1)

print(f"Key loaded: {key[:8]}... (length: {len(key)})")

url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:5000", 
    "X-Title": "AgentLeeOps Debug"
}
models = [
    "x-ai/grok-code-fast-1",
    "anthropic/claude-3-opus",      # Standard Opus
    "anthropic/claude-3.5-opus",    # Hypothetical?
    "anthropic/claude-opus-4.5"     # User request
]

for model in models:
    data = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}]
    }

    try:
        print(f"\n--- Testing {model} ---")
        resp = requests.post(url, headers=headers, json=data)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
             print("Success!")
        else:
             print(f"Error: {resp.text[:200]}")
    except Exception as e:
        print(f"Exception: {e}")
    except Exception as e:
        print(f"Exception: {e}")
