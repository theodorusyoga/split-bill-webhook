import asyncio
import json
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VELLUM_API_KEY = os.getenv("VELLUM_API_KEY")
VELLUM_WORKFLOW_NAME = os.getenv("VELLUM_WORKFLOW_NAME", "telegram-split-bill-bot")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
TELEGRAM_FILE_API = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"
VELLUM_EXECUTE_URL = "https://api.vellum.ai/v1/execute-workflow"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_telegram_file_url(file_id: str) -> str | None:
    """Call Telegram getFile API and return the full download URL."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        data = resp.json()
        if data.get("ok"):
            file_path = data["result"]["file_path"]
            return f"{TELEGRAM_FILE_API}/{file_path}"
    return None


async def call_vellum(chat_id: int, message_id: int, user_name: str, text: str, image_url: str | None):
    """Execute the Vellum workflow with the extracted Telegram data."""
    inputs = [
        {"name": "chat_id", "type": "NUMBER", "value": chat_id},
        {"name": "message_id", "type": "NUMBER", "value": message_id},
        {"name": "user_name", "type": "STRING", "value": user_name},
        {"name": "message", "type": "STRING", "value": text or ""},
        {"name": "image_url", "type": "STRING", "value": image_url or ""},
    ]

    payload = {
        "workflow_deployment_name": VELLUM_WORKFLOW_NAME,
        "inputs": inputs,
    }

    headers = {
        "X-API-KEY": VELLUM_API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(VELLUM_EXECUTE_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


def extract_file_id(message: dict) -> str | None:
    """Extract file_id from document, photo, or compressed image."""
    if "document" in message:
        return message["document"]["file_id"]
    if "photo" in message and message["photo"]:
        return message["photo"][-1]["file_id"]
    return None


async def process_message(chat_id: int, message_id: int, user_name: str, text: str, image_url: str | None):
    """Run Vellum in background (Vellum handles Telegram reply)."""
    try:
        result = await call_vellum(chat_id, message_id, user_name, text, image_url)
        logger.info("Vellum response: %s", result)
    except httpx.HTTPStatusError as e:
        logger.error("Vellum API error: %s — %s", e.response.status_code, e.response.text)
    except Exception as e:
        logger.error("Unexpected error: %s", e)


def handler(event, context):
    """Netlify Function handler for Telegram webhook."""
    try:
        body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        logger.info("Received update: %s", body)

        message = body.get("message")
        if not message:
            return {"statusCode": 200, "body": json.dumps({"ok": True, "detail": "no message"})}

        chat_id: int = message["chat"]["id"]
        message_id: int = message["message_id"]
        user_name: str = message["from"].get("username") or message["from"].get("first_name", "unknown")
        text: str = message.get("text") or message.get("caption") or ""

        # Resolve image URL if photo/document is attached
        image_url: str | None = None
        file_id = extract_file_id(message)
        if file_id:
            image_url = asyncio.run(get_telegram_file_url(file_id))
            logger.info("Resolved image URL: %s", image_url)

        # Process in background (fire and forget for Netlify)
        asyncio.run(process_message(chat_id, message_id, user_name, text, image_url))

        return {"statusCode": 200, "body": json.dumps({"ok": True})}

    except Exception as e:
        logger.error("Webhook error: %s", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
