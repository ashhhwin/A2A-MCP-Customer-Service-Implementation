import uuid
import time
import json
import logging
import sys
import os
import requests
import asyncio
from datetime import datetime

# MCP SDK Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------------------------------------------------
# 1. Agent Card & A2A Schema
# ---------------------------------------------------------

def create_a2a_message(sender_id, recipient_id, intent, content, msg_type="request", corr_id=None):
    """Constructs a compliant A2A message."""
    return {
        "message_id": str(uuid.uuid4()),
        "from": sender_id,
        "to": recipient_id,
        "type": msg_type,
        "intent": intent,
        "payload": content if content else {},
        "correlation_id": corr_id or str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat()
    }

def check_message_schema(message: dict):
    required = ["message_id", "from", "to", "type", "intent", "payload", "correlation_id"]
    missing = [f for f in required if f not in message]
    if missing:
        raise ValueError(f"Invalid A2A Message. Missing: {missing}")
    return True

def generate_error_response(orig_message, error_text):
    return create_a2a_message(
        sender_id=orig_message.get("to", "unknown"),
        recipient_id=orig_message.get("from", "unknown"),
        intent=orig_message.get("intent", "error"),
        msg_type="error",
        corr_id=orig_message.get("correlation_id"),
        content={"error": str(error_text)}
    )

# ---------------------------------------------------------
# 2. Agent Connector (The Client Logic)
# ---------------------------------------------------------
class AgentConnector:
    def __init__(self, timeout_sec=5, max_attempts=3):
        self.timeout = timeout_sec
        self.max_attempts = max_attempts
        # Determine path to MCP server app
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
    # --- A2A Communication (HTTP between Agents) ---
    def send_message(self, target_url, message: dict):
        """Sends an A2A message to another agent via HTTP."""
        try:
            check_message_schema(message)
            logging.info(f"[A2A-SEND] To: {target_url} | Intent: {message.get('intent')}")
            
            resp = requests.post(f"{target_url}/a2a", json=message, timeout=self.timeout)
            
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"status": "error", "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            logging.error(f"[A2A-FAIL] {e}")
            return {"status": "error", "error": str(e)}

    # --- MCP Tool Invocation (Stdio to MCP Server) ---
    async def invoke_tool(self, tool_name: str, arguments: dict):
        """
        Connects to the MCP server via Stdio, calls the tool, and returns the result.
        This is the 'Independent MCP Client' logic required by the professor.
        """
        logging.info(f"[MCP-START] Calling {tool_name}...")

        # Server Parameters: Run 'python -m mcp_server.app'
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.app"],
            env=os.environ.copy() # Pass current env (PATH, etc)
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 1. Initialize
                    await session.initialize()
                    
                    # 2. Call Tool
                    # Note: We assume the MCP server returns a JSON string, so we parse it.
                    result = await session.call_tool(tool_name, arguments)
                    
                    # 3. Parse Result (Standard MCP tools return a list of content blocks)
                    if result and hasattr(result, 'content') and result.content:
                        text_content = result.content[0].text
                        try:
                            # Our tools return JSON strings, so we parse them back to dicts
                            return json.loads(text_content)
                        except:
                            return text_content
                    
                    return {"status": "error", "data": "No content returned from tool"}

        except Exception as e:
            logging.error(f"[MCP-ERROR] {e}")
            return {"status": "error", "error": str(e)}

    # Helper wrapper for synchronous agents calling async MCP
    def invoke_tool_sync(self, tool_name, arguments):
        """Helper to run async tool call in sync context"""
        return asyncio.run(self.invoke_tool(tool_name, arguments))
'''
import uuid
import time
import json
import logging
from datetime import datetime
import requests

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(
    filename="logs/agent_comm.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------------------------------------------------
# A2A Message Utilities
# ---------------------------------------------------------
def create_a2a_message(sender_id, recipient_id, intent, content, msg_type="request", corr_id=None):
    """Construct a canonical A2A message."""
    return {
        "message_id": str(uuid.uuid4()),
        "from": sender_id,
        "to": recipient_id,
        "type": msg_type,                  # request | response | event
        "intent": intent,
        "payload": content if content else {},
        "correlation_id": corr_id or str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat()
    }


def check_message_schema(message: dict):
    """Ensure required fields exist."""
    fields = [
        "message_id", "from", "to", "type",
        "intent", "payload", "correlation_id", "timestamp"
    ]
    for f in fields:
        if f not in message:
            raise ValueError(f"Missing field in A2A message: {f}")
    return True


def generate_error_response(orig_message, error_text):
    """Standardized A2A error reply."""
    return create_a2a_message(
        sender_id=orig_message["to"],
        recipient_id=orig_message["from"],
        intent=orig_message["intent"],
        msg_type="response",
        corr_id=orig_message["correlation_id"],
        content={
            "status": "error",
            "error": error_text
        }
    )


# ---------------------------------------------------------
# Agent Networking Client
# ---------------------------------------------------------
class AgentConnector:
    def __init__(self, timeout_sec=5, max_attempts=3):
        self.timeout = timeout_sec
        self.max_attempts = max_attempts

    # ---------------------------------------------------------
    # A2A Communication
    # ---------------------------------------------------------
    def send_message(self, target_url, message: dict):
        """
        Send an A2A message with retry logic.
        Returns {status: ok|error, data: ...}
        """
        check_message_schema(message)
        corr_id = message["correlation_id"]

        for attempt in range(1, self.max_attempts + 1):
            try:
                logging.info(f"[A2A-SEND] cid={corr_id} → {target_url} | {json.dumps(message)}")

                resp = requests.post(
                    f"{target_url}/a2a",
                    json=message,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )

                if resp.status_code == 200:
                    data = resp.json()
                    logging.info(f"[A2A-RECV] cid={corr_id} | {json.dumps(data)}")
                    return {"status": "ok", "data": data}

                # non-200 but server responded
                logging.error(f"[A2A-FAIL] cid={corr_id} http={resp.status_code} | {resp.text}")
                return {"status": "error", "data": resp.text}

            except Exception as e:
                logging.warning(f"[A2A-RETRY] cid={corr_id} attempt={attempt} | {e}")
                time.sleep(2 ** (attempt - 1))

        return {"status": "error", "data": "Exceeded retry attempts"}

    # ---------------------------------------------------------
    # MCP Tool Invocation
    # ---------------------------------------------------------
    def invoke_tool(self, tool_name, parameters, mcp_url="http://127.0.0.1:8000"):
        """
        Call MCP server tools with retries.
        POST /tool/{tool_name}
        """
        endpoint = f"{mcp_url}/tool/{tool_name}"

        for attempt in range(1, self.max_attempts + 1):
            try:
                logging.info(f"[MCP-CALL] tool={tool_name} | {json.dumps(parameters)}")
                resp = requests.post(
                    endpoint,
                    json=parameters,
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout
                )

                if resp.status_code == 200:
                    result = resp.json()
                    logging.info(f"[MCP-OK] tool={tool_name} | {json.dumps(result)}")
                    return {"status": "ok", "data": result}

                logging.error(f"[MCP-FAIL] tool={tool_name} http={resp.status_code} | {resp.text}")
                return {"status": "error", "data": resp.text}

            except Exception as e:
                logging.warning(f"[MCP-RETRY] tool={tool_name} attempt={attempt} | {e}")
                time.sleep(2 ** (attempt - 1))

        return {"status": "error", "data": "Exceeded retry attempts"}
'''