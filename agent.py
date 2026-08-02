import os
import json
import time
import requests
import sys
from datetime import datetime, timezone

HF_TOKEN = os.environ.get("HF_TOKEN", "")
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
# Offizieller, stabiler Hugging Face Router-Endpunkt
API_URL = f"https://router.huggingface.co/v1/chat/completions"

# Eingabe ermitteln
prompt = os.environ.get("DISPATCH_PROMPT") or os.environ.get("MANUAL_PROMPT") or "Status Check"

# Speicher & Instruktionen laden
memory_file = "memory.json"
instructions_file = "instructions.md"

try:
    with open(memory_file, "r", encoding="utf-8") as f:
        loaded_data = json.load(f)
        if isinstance(loaded_data, list):
            memory = {"history": loaded_data, "status": "idle", "last_updated": ""}
        elif isinstance(loaded_data, dict):
            memory = loaded_data
        else:
            memory = {"history": [], "status": "idle", "last_updated": ""}
except Exception:
    memory = {"history": [], "status": "idle", "last_updated": ""}

if "history" not in memory or not isinstance(memory["history"], list):
    memory["history"] = []

try:
    with open(instructions_file, "r", encoding="utf-8") as f:
        instructions = f.read()
except Exception:
    instructions = "Du bist JARVIS, ein autonomer Agent mit Fähigkeit zur Tool-Erstellung."

system_prompt = f"""
{instructions}

WICHTIGE REGELN FÜR AUTONOMIE & DIFF-AUTHORING:
1. Wenn du eine Aufgabe löst, die Code, ein neues Tool oder eine Skriptänderung erfordert, gib IMMER einen sauberen Code-Diff im Unified-Diff-Format aus, umschlossen von ```diff ... ```.
2. Antworte präzise, lösungsorientiert und professionell auf Deutsch.
3. Wenn kein Code geändert werden muss, antworte normal ohne Diff-Block.
"""

messages = [{"role": "system", "content": system_prompt}]
for entry in memory.get("history", [])[-8:]:
    if isinstance(entry, dict):
        messages.append({"role": entry.get("role", "user"), "content": entry.get("content", "")})
messages.append({"role": "user", "content": prompt})

headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
payload = {
    "model": MODEL_ID,
    "messages": messages,
    "max_tokens": 1200,
    "temperature": 0.3
}

assistant_reply = "Fehler: Keine Antwort erhalten."
status = "success"

for attempt in range(3):
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=45
        )
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
        assistant_reply = f"Systemfehler bei Inferenz: {str(e)}"
        status = "error"
        time.sleep(3)

# History & State aktualisieren
memory["history"].append({"role": "user", "content": prompt, "timestamp": datetime.now(timezone.utc).isoformat()})
memory["history"].append({"role": "assistant", "content": assistant_reply, "timestamp": datetime.now(timezone.utc).isoformat()})
memory["status"] = status
memory["last_updated"] = datetime.now(timezone.utc).isoformat()

with open(memory_file, "w", encoding="utf-8") as f:
    json.dump(memory, f, indent=2, ensure_ascii=False)

sys.exit(0)
