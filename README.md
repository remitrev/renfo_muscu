# renfo_muscu

Tous les matins avant 7h (heure de Paris), une GitHub Action lit ton calendrier
d'entraînement Coros et t'envoie une notif Discord si une séance de renfo
est prévue ce jour-là.

GitHub retarde ou saute souvent les lancements planifiés : le workflow est donc
programmé plusieurs fois entre 5h20 et 7h, et seule la première tentative qui
passe envoie la notif (les suivantes voient qu'elle est déjà partie).

## Mise en place

1. Sur Discord : Paramètres du salon → Intégrations → Webhooks → Nouveau webhook → copier l'URL.
2. Sur GitHub : Settings → Secrets and variables → Actions → **Secrets** :
   - `COROS_EMAIL` : email du compte Coros
   - `COROS_PASSWORD` : mot de passe Coros
   - `DISCORD_WEBHOOK_URL` : l'URL du webhook
3. (Optionnel) onglet **Variables** :
   - `COROS_REGION` : `eu` (défaut), `us` ou `asia`
   - `NOTIFY_WHEN_NONE` : `true` pour aussi recevoir un message les jours sans renfo
4. Tester : onglet Actions → « Check renfo du jour » → Run workflow.

## Détection du renfo

Une séance compte comme du renfo si son type de sport Coros est « Strength »
ou si son nom contient `renfo`, `muscu`, `strength`, `gainage`, `ppg` ou `core`.

## En local

```bash
COROS_EMAIL=... COROS_PASSWORD=... DRY_RUN=true python check_renfo.py
```

⚠️ L'API utilisée est celle (non officielle) de Coros Training Hub : elle peut changer sans prévenir.
