import os
import json
import time
import requests
import sys
from datetime import datetime, timezone

HF_TOKEN = os.environ.get("HF_TOKEN", "")
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

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

REGELN FÜR DEINE ANTWORTEN:
1. Antworte präzise, direkt und auf Deutsch auf die Anfrage des Nutzers.
2. Wenn du Code oder ein neues Tool erstellst, gib den Code in einem sauberen Diff-Block aus (```diff ... ```).
3. Verändere niemals die agent.py, es sei denn, der Benutzer fordert es absolut explizit in diesem Prompt.
"""

full_context = f"System: {system_prompt}\n"
for entry in memory.get("history", [])[-6:]:
    if isinstance(entry, dict):
        role = entry.get("role", "user")
        content = entry.get("content", "")
        full_context += f"{role.capitalize()}: {content}\n"
full_context += f"User: {prompt}\nAssistant:"

headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
payload = {
    "inputs": full_context,
    "parameters": {
        "max_new_tokens": 1000,
        "temperature": 0.3,
        "return_full_text": False
    }
}

assistant_reply = "Fehler: Keine Antwort von der KI erhalten."
status = "success"

for attempt in range(3):
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                assistant_reply = data[0]["generated_text"].strip()
            elif isinstance(data, dict) and "generated_text" in data:
                assistant_reply = data["generated_text"].strip()
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
