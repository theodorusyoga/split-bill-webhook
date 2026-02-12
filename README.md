# Split Bill Telegram Bot (Vellum.ai Webhook)

Telegram webhook → Vellum.ai workflow for splitting bills via chat.

Deployed as **Netlify Functions** (serverless).

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with FastAPI (local only)
uvicorn main:app --reload --port 8000
```

## Deployment to Netlify

1. Push to GitHub
2. Connect repo to Netlify
3. Set environment variables in Netlify dashboard:
   - `TELEGRAM_BOT_TOKEN`
   - `VELLUM_API_KEY`
   - `VELLUM_WORKFLOW_NAME`

4. Netlify auto-deploys from `netlify/functions/`

## Endpoints

| Method | Path                    | Description              |
|--------|-------------------------|--------------------------|
| POST   | `/.netlify/functions/webhook` | Telegram webhook handler |
| GET    | `/.netlify/functions/health`  | Health check             |

## Set Telegram Webhook

After deployment, set the webhook to your Netlify URL:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_NETLIFY_DOMAIN/.netlify/functions/webhook"}'
```

## Project Structure

```
.
├── netlify/functions/
│   ├── webhook.py    # Telegram webhook handler
│   └── health.py     # Health check
├── main.py           # FastAPI version (local dev only)
├── netlify.toml      # Netlify config
├── requirements.txt  # Dependencies
└── .env              # Environment variables (not committed)
```
