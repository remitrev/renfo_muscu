"""Lit le calendrier Coros du jour et envoie une notif Discord s'il y a du renfo.

Utilise l'API (non officielle) de Coros Training Hub.

Variables d'environnement :
  COROS_EMAIL          email du compte Coros (obligatoire)
  COROS_PASSWORD       mot de passe Coros (obligatoire)
  DISCORD_WEBHOOK_URL  URL du webhook Discord (obligatoire)
  COROS_REGION         eu (défaut), us ou asia
  TZ_NAME              fuseau horaire pour « aujourd'hui » (défaut Europe/Paris)
  NOTIFY_WHEN_NONE     "true" pour aussi notifier les jours sans renfo (défaut false)
  DRY_RUN              "true" pour afficher le message sans l'envoyer
"""

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_URLS = {
    "eu": "https://teameuapi.coros.com",
    "us": "https://teamapi.coros.com",
    "asia": "https://teamcnapi.coros.com",
}
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
# sportType des séances planifiées dans Coros : 4 = Strength
STRENGTH_SPORT_TYPES = {4, 402}
STRENGTH_KEYWORDS = ("renfo", "muscu", "strength", "gainage", "ppg", "core")


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "oui")


def http_json(method, url, headers=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else {}


def check(body, context):
    if body.get("result") != "0000":
        raise RuntimeError(
            f"Erreur Coros ({context}) : {body.get('message')} (result={body.get('result')})"
        )
    return body.get("data") or {}


def login(base, email, password):
    body = http_json(
        "POST",
        base + "/account/login",
        body={
            "account": email,
            "accountType": 2,
            "pwd": hashlib.md5(password.encode()).hexdigest(),
        },
    )
    data = check(body, "login")
    return data["accessToken"], data["userId"]


def fetch_schedule(base, token, user_id, day):
    params = urllib.parse.urlencode(
        {"startDate": day, "endDate": day, "supportRestExercise": 1}
    )
    body = http_json(
        "GET",
        f"{base}/training/schedule/query?{params}",
        headers={"accessToken": token, "yfheader": json.dumps({"userId": user_id})},
    )
    return check(body, "schedule")


def todays_workouts(schedule, day):
    """Associe chaque entrée du calendrier du jour à son programme (séance)."""
    programs = {}
    for program in schedule.get("programs") or []:
        programs[(str(program.get("planId", "")), str(program.get("idInPlan", "")))] = program
        programs.setdefault(("", str(program.get("idInPlan", ""))), program)

    workouts = []
    for entity in schedule.get("entities") or []:
        if str(entity.get("happenDay", "")) != day:
            continue
        key = (str(entity.get("planId", "")), str(entity.get("idInPlan", "")))
        program = programs.get(key) or programs.get(("", key[1])) or {}
        workouts.append(
            {
                "name": program.get("name") or entity.get("name") or "Séance sans nom",
                "sport_type": program.get("sportType", entity.get("sportType")),
                "duration": program.get("estimatedTime") or program.get("duration"),
            }
        )
    return workouts


def is_strength(workout):
    try:
        if int(workout["sport_type"]) in STRENGTH_SPORT_TYPES:
            return True
    except (TypeError, ValueError):
        pass
    name = workout["name"].lower()
    return any(k in name for k in STRENGTH_KEYWORDS)


def format_duration(seconds):
    try:
        minutes = int(seconds) // 60
    except (TypeError, ValueError):
        return None
    if minutes <= 0:
        return None
    return f"{minutes // 60}h{minutes % 60:02d}" if minutes >= 60 else f"{minutes} min"


def build_message(today, strength, others):
    date_txt = today.strftime("%d/%m/%Y")
    if not strength:
        lines = [f"😴 Pas de renfo prévu aujourd'hui ({date_txt})."]
    else:
        lines = [f"💪 **Renfo prévu aujourd'hui ({date_txt}) !**"]
        for w in strength:
            duration = format_duration(w["duration"])
            lines.append(f"• **{w['name']}**" + (f" — {duration}" if duration else ""))
    if others:
        lines.append("")
        lines.append("Autres séances : " + ", ".join(w["name"] for w in others))
    return "\n".join(lines)


def send_discord(webhook, content):
    http_json("POST", webhook, body={"content": content, "username": "Coach Renfo"})


def main():
    email = os.environ.get("COROS_EMAIL")
    password = os.environ.get("COROS_PASSWORD")
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    dry_run = env_flag("DRY_RUN")
    missing = [n for n, v in (("COROS_EMAIL", email), ("COROS_PASSWORD", password)) if not v]
    if not webhook and not dry_run:
        missing.append("DISCORD_WEBHOOK_URL")
    if missing:
        sys.exit(f"Variables manquantes : {', '.join(missing)}")

    region = os.environ.get("COROS_REGION", "eu").strip().lower() or "eu"
    base = BASE_URLS.get(region, BASE_URLS["eu"])
    today = datetime.now(ZoneInfo(os.environ.get("TZ_NAME") or "Europe/Paris")).date()
    day = today.strftime("%Y%m%d")

    token, user_id = login(base, email, password)
    workouts = todays_workouts(fetch_schedule(base, token, user_id, day), day)
    strength = [w for w in workouts if is_strength(w)]
    others = [w for w in workouts if not is_strength(w)]
    print(f"{day} : {len(workouts)} séance(s), dont {len(strength)} de renfo")

    if not strength and not env_flag("NOTIFY_WHEN_NONE"):
        print("Pas de renfo aujourd'hui, pas de notif.")
        return

    message = build_message(today, strength, others)
    print(message)
    if dry_run:
        print("DRY_RUN : message non envoyé.")
        return
    send_discord(webhook, message)
    print("Notif Discord envoyée.")


if __name__ == "__main__":
    main()
