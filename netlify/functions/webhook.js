const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const VELLUM_API_KEY = process.env.VELLUM_API_KEY;
const VELLUM_WORKFLOW_NAME = process.env.VELLUM_WORKFLOW_NAME || "telegram-split-bill-bot";

const TELEGRAM_API = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}`;
const TELEGRAM_FILE_API = `https://api.telegram.org/file/bot${TELEGRAM_BOT_TOKEN}`;
const VELLUM_EXECUTE_URL = "https://api.vellum.ai/v1/execute-workflow";

async function getTelegramFileUrl(fileId) {
  const resp = await fetch(`${TELEGRAM_API}/getFile?file_id=${fileId}`);
  const data = await resp.json();
  if (data.ok) {
    return `${TELEGRAM_FILE_API}/${data.result.file_path}`;
  }
  return null;
}

async function callVellum(chatId, messageId, userName, text, imageUrl) {
  const payload = {
    workflow_deployment_name: VELLUM_WORKFLOW_NAME,
    inputs: [
      { name: "chat_id", type: "NUMBER", value: chatId },
      { name: "message_id", type: "NUMBER", value: messageId },
      { name: "user_name", type: "STRING", value: userName },
      { name: "message", type: "STRING", value: text || "" },
      { name: "image_url", type: "STRING", value: imageUrl || "" },
    ],
  };

  const resp = await fetch(VELLUM_EXECUTE_URL, {
    method: "POST",
    headers: {
      "X-API-KEY": VELLUM_API_KEY,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const errorText = await resp.text();
    console.error(`Vellum API error: ${resp.status} — ${errorText}`);
    return null;
  }

  return await resp.json();
}

function extractFileId(message) {
  if (message.document) {
    return message.document.file_id;
  }
  if (message.photo && message.photo.length > 0) {
    return message.photo[message.photo.length - 1].file_id;
  }
  return null;
}

exports.handler = async (event, context) => {
  try {
    const body = JSON.parse(event.body);
    console.log("Received update:", JSON.stringify(body));

    const message = body.message;
    if (!message) {
      return {
        statusCode: 200,
        body: JSON.stringify({ ok: true, detail: "no message" }),
      };
    }

    const chatId = message.chat.id;
    const messageId = message.message_id;
    const userName = message.from.username || message.from.first_name || "unknown";
    const text = message.text || message.caption || "";

    // Resolve image URL if photo/document is attached
    let imageUrl = null;
    const fileId = extractFileId(message);
    if (fileId) {
      imageUrl = await getTelegramFileUrl(fileId);
      console.log("Resolved image URL:", imageUrl);
    }

    // Forward to Vellum (Vellum handles Telegram reply)
    const result = await callVellum(chatId, messageId, userName, text, imageUrl);
    console.log("Vellum response:", JSON.stringify(result));

    return {
      statusCode: 200,
      body: JSON.stringify({ ok: true }),
    };
  } catch (err) {
    console.error("Webhook error:", err);
    return {
      statusCode: 200,
      body: JSON.stringify({ ok: true }),
    };
  }
};
