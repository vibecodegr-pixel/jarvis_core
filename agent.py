import os
import json
import time
import requests
import sys
from datetime import datetime, timezone

HF_TOKEN = os.environ.get("HF_TOKEN", "")
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
# Der neue, stabile OpenAI-kompatible Router-Endpunkt von Hugging Face
API_URL = "https://router.huggingface.co/v1/chat/completions"

prompt = os.environ.get("DISPATCH_PROMPT") or os.environ.get("MANUAL_PROMPT") or "Status Check"

memory_file = "memory.json"
instructions_file = "instructions.md"

try:
    with open(memory_file, "r", encoding="utf-8") as f:
        memory = json.load(f)
except Exception:
    memory = {"history": [], "status": "idle", "last_updated": ""}

if not isinstance(memory, dict):
    memory = {"history": [], "status": "idle", "last_updated": ""}
if "history" not in memory or not isinstance(memory["history"], list):
    memory["history"] = []

try:
    with open(instructions_file, "r", encoding="utf-8") as f:
        instructions = f.read()
except Exception:
    instructions = "Du bist JARVIS, ein autonomer Agent."

system_prompt = f"""
{instructions}

REGELN:
1. Antworte präzise, direkt und auf Deutsch.
2. Wenn der Nutzer ein Tool fordert, erstelle den Code.
"""

messages = [{"role": "system", "content": system_prompt}]
for entry in memory.get("history", [])[-6:]:
    if isinstance(entry, dict):
        messages.append({"role": entry.get("role", "user"), "content": entry.get("content", "")})
messages.append({"role": "user", "content": prompt})

headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
payload = {
    "model": MODEL_ID,
    "messages": messages,
    "max_tokens": 1000,
    "temperature": 0.3
}

assistant_reply = "Fehler: Keine Antwort von der KI erhalten."
status = "success"

for attempt in range(3):
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                assistant_reply = data["choices"][0]["message"]["content"].strip()
            else:
                assistant_reply = str(data)
            status = "success"
            break
        else:
            time.sleep(3)
    except Exception as e:
        assistant_reply = f"Inferenz-Fehler: {str(e)}"
        status = "error"
        time.sleep(3)

memory["history"].append({"role": "user", "content": prompt, "timestamp": datetime.now(timezone.utc).isoformat()})
memory["history"].append({"role": "assistant", "content": assistant_reply, "timestamp": datetime.now(timezone.utc).isoformat()})
memory["status"] = status
memory["last_updated"] = datetime.now(timezone.utc).isoformat()

with open(memory_file, "w", encoding="utf-8") as f:
    json.dump(memory, f, indent=2, ensure_ascii=False)

sys.exit(0)
