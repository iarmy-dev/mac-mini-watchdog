#!/usr/bin/env python3
# Watchdog externe Mac Mini — poll heartbeat ntfy, alerte Telegram au changement d'etat.
# Secrets via env: TELEGRAM_TOKEN, TELEGRAM_CHAT. Pas de secret en clair dans le repo.
import os, sys, json, time, urllib.request, urllib.parse

NTFY_TOPIC = "macmini-heartbeat-k7m9x2"   # battement de coeur emis par le Mac Mini
STALE_MIN  = 15                            # pas de heartbeat depuis >15 min => DOWN
STATE_FILE = "state.json"

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT  = os.environ["TELEGRAM_CHAT"]

def last_heartbeat_age_min():
    since = int(time.time()) - 3600
    url = f"https://ntfy.sh/{NTFY_TOPIC}/json?poll=1&since={since}"
    req = urllib.request.Request(url, headers={"User-Agent": "watchdog"})
    times = []
    with urllib.request.urlopen(req, timeout=30) as r:
        for line in r.read().decode().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("event") == "message" and d.get("time"):
                times.append(d["time"])
    if not times:
        return None  # aucun heartbeat sur 1h
    return (time.time() - max(times)) / 60.0

def send(text):
    data = urllib.parse.urlencode({
        "chat_id": CHAT, "text": text, "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        json.loads(r.read().decode())

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"status": "unknown", "since": None}

def save_state(s):
    with open(STATE_FILE, "w") as f:
        json.dump(s, f)

def main():
    age = last_heartbeat_age_min()
    if age is None:
        status, detail = "DOWN", "aucun heartbeat depuis &gt;1h"
    elif age > STALE_MIN:
        status, detail = "DOWN", f"dernier heartbeat il y a {age:.0f} min"
    else:
        status, detail = "UP", f"heartbeat il y a {age:.0f} min"

    prev = load_state()
    now = time.strftime("%d/%m %H:%M", time.localtime())
    print(f"status={status} ({detail}) prev={prev.get('status')}")

    if status != prev.get("status"):
        if status == "DOWN":
            send(f"\U0001F6A8 <b>MAC MINI DOWN</b>\n{detail}\nDetecte le {now}")
        else:
            send(f"\u2705 <b>Mac Mini de retour</b>\n{detail}\nLe {now}")
        save_state({"status": status, "since": now})
        # signaler a l'action qu'il faut commit le nouveau state
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a") as f:
                f.write("changed=true\n")
    else:
        print("etat inchange, pas de notif")

if __name__ == "__main__":
    main()
