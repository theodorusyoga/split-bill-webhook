const WHATSAPP_VERIFY_TOKEN = process.env.WHATSAPP_VERIFY_TOKEN;
const WHATSAPP_ACCESS_TOKEN = process.env.WHATSAPP_ACCESS_TOKEN;
const VELLUM_API_KEY = process.env.VELLUM_API_KEY;
const VELLUM_WORKFLOW_NAME =
  process.env.VELLUM_WA_WORKFLOW_NAME || "whatsapp-split-bill-bot";

const GRAPH_API_VERSION = "v21.0";
const GRAPH_API_BASE = `https://graph.facebook.com/${GRAPH_API_VERSION}`;
const VELLUM_EXECUTE_URL = "https://api.vellum.ai/v1/execute-workflow";

// Fetch a media URL from WhatsApp Cloud API using the media ID
async function getWhatsAppMediaUrl(mediaId) {
  const resp = await fetch(`${GRAPH_API_BASE}/${mediaId}`, {
    headers: { Authorization: `Bearer ${WHATSAPP_ACCESS_TOKEN}` },
  });
  const data = await resp.json();
  return data.url || null;
}

async function callVellum(chatId, messageId, userName, text, imageUrl) {
  const payload = {
    workflow_deployment_name: VELLUM_WORKFLOW_NAME,
    inputs: [
      { name: "chat_id", type: "STRING", value: chatId },
      { name: "message_id", type: "STRING", value: messageId },
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

exports.handler = async (event, context) => {
  // GET — Facebook webhook verification
  if (event.httpMethod === "GET") {
    const params = event.queryStringParameters || {};
    const mode = params["hub.mode"];
    const token = params["hub.verify_token"];
    const challenge = params["hub.challenge"];

    if (mode === "subscribe" && token === WHATSAPP_VERIFY_TOKEN) {
      console.log("Webhook verified successfully");
      return {
        statusCode: 200,
        body: challenge,
      };
    }

    return {
      statusCode: 403,
      body: "Forbidden",
    };
  }

  // POST — incoming WhatsApp messages
  try {
    const body = JSON.parse(event.body);
    console.log("Received WhatsApp update:", JSON.stringify(body));

    const entry = body.entry;
    if (!entry || entry.length === 0) {
      return { statusCode: 200, body: JSON.stringify({ ok: true }) };
    }

    for (const e of entry) {
      const changes = e.changes || [];
      for (const change of changes) {
        if (change.field !== "messages") continue;

        const value = change.value;
        const messages = value.messages || [];
        const contacts = value.contacts || [];

        for (const message of messages) {
          const from = message.from; // sender phone number
          const messageId = message.id;
          const userName =
            contacts.length > 0
              ? contacts[0].profile?.name || from
              : from;

          let text = "";
          let imageUrl = null;

          if (message.type === "text") {
            text = message.text?.body || "";
          } else if (message.type === "image") {
            text = message.image?.caption || "";
            const mediaId = message.image?.id;
            if (mediaId) {
              imageUrl = await getWhatsAppMediaUrl(mediaId);
              console.log("Resolved WhatsApp image URL:", imageUrl);
            }
          } else if (message.type === "document") {
            text = message.document?.caption || "";
            const mediaId = message.document?.id;
            if (mediaId) {
              imageUrl = await getWhatsAppMediaUrl(mediaId);
              console.log("Resolved WhatsApp document URL:", imageUrl);
            }
          }

          const result = await callVellum(
            from,
            messageId,
            userName,
            text,
            imageUrl
          );
          console.log("Vellum response:", JSON.stringify(result));
        }
      }
    }

    return { statusCode: 200, body: JSON.stringify({ ok: true }) };
  } catch (err) {
    console.error("WhatsApp webhook error:", err);
    return { statusCode: 200, body: JSON.stringify({ ok: true }) };
  }
};
