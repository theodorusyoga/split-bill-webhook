import asyncio
import os
import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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

app = FastAPI(title="Split Bill Telegram Bot")


async def get_telegram_file_url(file_id: str) -> str | None:
    """Call Telegram getFile API and return the full download URL."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        data = resp.json()
        if data.get("ok"):
            file_path = data["result"]["file_path"]
            return f"{TELEGRAM_FILE_API}/{file_path}"
    return None


async def send_telegram_message(chat_id: int, text: str, reply_to: int | None = None):
    """Send a text message back to the Telegram chat."""
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)


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
    # Document (uncompressed file / image sent as file)
    if "document" in message:
        return message["document"]["file_id"]
    # Photo (compressed, array sorted by size — last = largest)
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


@app.post("/webhook")
async def telegram_webhook(request: Request):
    body = await request.json()
    logger.info("Received update: %s", body)

    message = body.get("message")
    if not message:
        return JSONResponse({"ok": True, "detail": "no message"})

    chat_id: int = message["chat"]["id"]
    message_id: int = message["message_id"]
    user_name: str = message["from"].get("username") or message["from"].get("first_name", "unknown")
    text: str = message.get("text") or message.get("caption") or ""

    # Resolve image URL if photo/document is attached
    image_url: str | None = None
    file_id = extract_file_id(message)
    if file_id:
        image_url = await get_telegram_file_url(file_id)
        logger.info("Resolved image URL: %s", image_url)

    # Kick off background processing, respond immediately
    asyncio.create_task(process_message(chat_id, message_id, user_name, text, image_url))
    return JSONResponse({"ok": True})


@app.get("/health")
async def health():
    return {"status": "ok"}
