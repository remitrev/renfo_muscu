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

## Déclenchement à l'heure pile avec cron-job.org

Les crons GitHub peuvent avoir du retard ou sauter. Pour une notif fiable avant 7h,
cron-job.org peut déclencher le workflow lui-même :

1. Crée un token GitHub *fine-grained* (Settings → Developer settings → Fine-grained tokens) :
   accès au seul dépôt `renfo_muscu`, permission **Actions : Read and write**.
2. Sur cron-job.org, crée un cron job :
   - URL : `https://api.github.com/repos/remitrev/renfo_muscu/actions/workflows/renfo.yml/dispatches`
   - Horaire : tous les jours à 6h45, fuseau `Europe/Paris`
   - Méthode `POST`, en-têtes `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`,
     `Content-Type: application/json`
   - Corps : `{"ref":"main","inputs":{"once":"true"}}`

Avec `once`, rien n'est envoyé si une tentative GitHub a déjà fait la vérification du jour.
