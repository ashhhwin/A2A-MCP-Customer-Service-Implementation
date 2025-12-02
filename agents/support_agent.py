from fastapi import FastAPI, Request
from agents.agent_client import AgentConnector, create_a2a_message, check_message_schema, generate_error_response
import uvicorn
import logging
import asyncio

app = FastAPI(title="Support Agent")
agent = AgentConnector()
DATA_AGENT_URL = "http://127.0.0.1:8101"

# -------------------------
# Logging setup
# -------------------------
logging.basicConfig(
    filename="logs/support_agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -------------------------
# Agent Card (REQUIRED)
# -------------------------
@app.get("/agent_card")
def get_card():
    return {
        "name": "Support Agent",
        "description": "Handles tickets, refunds, and support logic.",
        "input_schema": {"intent": "string", "payload": "object"},
        "tools": ["create_ticket", "list_tickets"],
        "a2a_protocol": "REST_HTTP_JSON"
    }

# -------------------------
# Intent handlers
# -------------------------
async def handle_support_intent(intent: str, payload: dict):
    """Async handler for each support intent."""
    customer_id = payload.get("customer_id")
    text = payload.get("text", "")

    if intent == "support_request":
        return {"status": "ok", "answer_text": f"Support request received: {text}"}

    elif intent == "refund_request":
        return {"status": "ok", "answer_text": "Refund initiated."}

    elif intent == "cancel_subscription":
        return {"status": "ok", "answer_text": "Subscription cancelled."}

    elif intent == "upgrade_request":
        return {"status": "ok", "answer_text": "Customer upgraded."}

    elif intent == "show_ticket_status":
        if not customer_id:
            return {"status": "error", "error": "Missing customer_id"}
        # Must await the tool call now
        return await agent.invoke_tool("list_tickets", {"customer_ids": [customer_id]})

    elif intent == "escalate_issue":
        issue_text = text
        # -------------------------
        # Negotiation / billing hook
        # -------------------------
        if "billing" in issue_text.lower():
            return {"status": "need_billing_context", "note": "Require billing info from data agent"}
        else:
            # Must await the tool call now
            return await agent.invoke_tool("create_ticket", {
                "customer_id": customer_id,
                "issue": issue_text,
                "priority": "medium"
            })

    else:
        return {"status": "error", "error": f"Unknown support intent: {intent}"}

# -------------------------
# A2A handler
# -------------------------
@app.post("/a2a")
async def a2a_handler(request: Request):
    msg = await request.json()
    try:
        check_message_schema(msg)
        intents = msg["intent"]
        payload = msg["payload"]
        cid = msg["correlation_id"]

        # Ensure intents is a list
        if not isinstance(intents, list):
            intents = [intents]

        logging.info(f"[A2A-RECEIVED] intents={intents} payload={payload}")

        # -------------------------
        # Process all intents asynchronously
        # -------------------------
        tasks = [handle_support_intent(intent, payload) for intent in intents]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        logging.info(f"[A2A-RESPONSE] results={results}")

        return create_a2a_message(
            sender_id="support_agent",
            recipient_id=msg["from"],
            intent=intents,
            msg_type="response",
            content=results,
            corr_id=cid
        )

    except Exception as e:
        logging.error(f"[A2A-ERROR] {msg} | {e}")
        return generate_error_response(msg, str(e))

# -------------------------
# Health endpoint
# -------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8102)
'''
from fastapi import FastAPI, Request
from agents.agent_client import AgentConnector, create_a2a_message, check_message_schema, generate_error_response
import uvicorn
import logging
import asyncio

app = FastAPI(title="Support Agent")
agent = AgentConnector()
DATA_AGENT_URL = "http://127.0.0.1:8101"

# -------------------------
# Logging setup
# -------------------------
logging.basicConfig(
    filename="logs/support_agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# -------------------------
# Intent handlers
# -------------------------
async def handle_support_intent(intent: str, payload: dict):
    """Async handler for each support intent."""
    customer_id = payload.get("customer_id")
    text = payload.get("text", "")

    if intent == "support_request":
        return {"status": "ok", "answer_text": f"Support request received: {text}"}

    elif intent == "refund_request":
        return {"status": "ok", "answer_text": "Refund initiated."}

    elif intent == "cancel_subscription":
        return {"status": "ok", "answer_text": "Subscription cancelled."}

    elif intent == "upgrade_request":
        return {"status": "ok", "answer_text": "Customer upgraded."}

    elif intent == "show_ticket_status":
        if not customer_id:
            return {"status": "error", "error": "Missing customer_id"}
        return agent.invoke_tool("list_tickets", {"customer_ids": [customer_id]})

    elif intent == "escalate_issue":
        issue_text = text
        # -------------------------
        # Negotiation / billing hook
        # -------------------------
        if "billing" in issue_text.lower():
            return {"status": "need_billing_context", "note": "Require billing info from data agent"}
        else:
            return agent.invoke_tool("create_ticket", {
                "customer_id": customer_id,
                "issue": issue_text,
                "priority": "medium"
            })

    else:
        return {"status": "error", "error": f"Unknown support intent: {intent}"}

# -------------------------
# A2A handler
# -------------------------
@app.post("/a2a")
async def a2a_handler(request: Request):
    msg = await request.json()
    try:
        check_message_schema(msg)
        intents = msg["intent"]
        payload = msg["payload"]
        cid = msg["correlation_id"]

        # Ensure intents is a list
        if not isinstance(intents, list):
            intents = [intents]

        logging.info(f"[A2A-RECEIVED] intents={intents} payload={payload}")

        # -------------------------
        # Process all intents asynchronously
        # -------------------------
        tasks = [handle_support_intent(intent, payload) for intent in intents]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        logging.info(f"[A2A-RESPONSE] results={results}")

        return create_a2a_message(
            sender_id="support_agent",
            recipient_id=msg["from"],
            intent=intents,
            msg_type="response",
            content=results,
            corr_id=cid
        )

    except Exception as e:
        logging.error(f"[A2A-ERROR] {msg} | {e}")
        return generate_error_response(msg, str(e))

# -------------------------
# Health endpoint
# -------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8102)
'''