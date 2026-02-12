# Split Bill Telegram Bot (Vellum.ai Webhook)

Telegram webhook → Vellum.ai workflow for splitting bills via chat.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --port 8000
```

## Expose to Telegram (for local dev)

Use ngrok or similar:

```bash
ngrok http 8000
```

Then set the webhook:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://YOUR_NGROK_URL/webhook"}'
```

## Endpoints

| Method | Path       | Description              |
|--------|------------|--------------------------|
| POST   | `/webhook` | Telegram webhook handler |
| GET    | `/health`  | Health check             |

## Environment Variables

| Variable              | Description                    |
|-----------------------|--------------------------------|
| `TELEGRAM_BOT_TOKEN`  | Telegram Bot API token         |
| `VELLUM_API_KEY`      | Vellum.ai API key              |
| `VELLUM_WORKFLOW_NAME` | Vellum workflow deployment name |
