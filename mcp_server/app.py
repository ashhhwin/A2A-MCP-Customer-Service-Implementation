import os
import sys
import json
import subprocess
from typing import Optional, List
from mcp.server.fastmcp import FastMCP

# Import db_utils handling both module and script execution contexts
try:
    from . import db_utils
except ImportError:
    import db_utils

# Initialize the FastMCP Server
# This handles the MCP protocol handshake (JSON-RPC via Stdio or SSE) automatically.
mcp = FastMCP("CustomerSupport", dependencies=["sqlite3"])

# Configuration
# Resolves paths relative to this file to ensure database connection works.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "support.db")

# ---------------------------------------------------------
# Tool Definitions
# The @mcp.tool() decorator automatically registers these 
# functions with the correct JSON schema for the Inspector.
# ---------------------------------------------------------

@mcp.tool()
def get_customer(customer_id: int) -> str:
    """Retrieves a customer by their ID."""
    result = db_utils.get_customer(DB_FILE, customer_id)
    return json.dumps(result)

@mcp.tool()
def list_customers(status: Optional[str] = None, tier: Optional[str] = None, limit: Optional[int] = 10) -> str:
    """Lists customers with optional filters for status or tier."""
    result = db_utils.list_customers(DB_FILE, status=status, tier=tier, limit=limit)
    return json.dumps(result)

@mcp.tool()
def update_customer(customer_id: int, data: dict) -> str:
    """Updates customer details (email, tier, billing_info)."""
    result = db_utils.update_customer(DB_FILE, customer_id, data)
    return json.dumps(result)

@mcp.tool()
def create_ticket(customer_id: int, issue: str, priority: str) -> str:
    """Creates a support ticket for a customer."""
    result = db_utils.create_ticket(DB_FILE, customer_id, issue, priority)
    return json.dumps(result)

@mcp.tool()
def get_customer_history(customer_id: int) -> str:
    """Retrieves ticket history for a specific customer."""
    result = db_utils.get_customer_history(DB_FILE, customer_id)
    return json.dumps(result)

@mcp.tool()
def list_tickets(customer_ids: List[int], status: Optional[str] = None, priority: Optional[str] = None) -> str:
    """Lists tickets for specific customers with optional filters."""
    result = db_utils.list_tickets_for_customers(DB_FILE, customer_ids, status=status, priority=priority)
    return json.dumps(result)

@mcp.tool()
def reset_db() -> str:
    """Resets the database to initial state using database_setup.py."""
    script_path = os.path.join(os.path.dirname(__file__), "database_setup.py")
    if os.path.exists(script_path):
        # Uses the current python executable to run the setup script
        subprocess.run([sys.executable, script_path], input=b"y\ny\n")
        return "Database reset completed."
    return "Error: database_setup.py not found."

if __name__ == "__main__":
    # mcp.run() detects the transport (Stdio/SSE) automatically based on environment
    mcp.run()
'''
import os
import subprocess
import json
import asyncio
from datetime import datetime
from typing import Optional, List, AsyncGenerator

from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import db_utils 

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_FILE = os.path.join(PROJECT_ROOT, "support.db")
LOG_FILE = os.path.join(os.path.dirname(__file__), "mcp.log")

app = FastAPI(title="Customer Support MCP Server")

# ------------------------
# Logging helper
# ------------------------
def log_msg(message: str):
    timestamp = datetime.utcnow()
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} - {message}\n")


# ------------------------
# Agent info
# ------------------------
AGENT_INFO = {
    "name": "CustomerSupportMCP",
    "version": "1.1",
    "tools": [
        "get_customer",
        "list_customers",
        "update_customer",
        "create_ticket",
        "get_customer_history",
        "list_tickets",
        "reset_db"
    ]
}


@app.get("/agent_card")
def agent_card():
    return AGENT_INFO


# ------------------------
# Pydantic models
# ------------------------
class GetCustomerReq(BaseModel):
    customer_id: int

class ListCustomersReq(BaseModel):
    status: Optional[str] = None
    tier: Optional[str] = None
    limit: Optional[int] = None

class UpdateCustomerReq(BaseModel):
    customer_id: int
    data: dict  # Can include email, tier, billing_info

class CreateTicketReq(BaseModel):
    customer_id: int
    issue: str
    priority: str

class HistoryReq(BaseModel):
    customer_id: int

class ListTicketsReq(BaseModel):
    customer_ids: List[int]
    status: Optional[str] = None
    priority: Optional[str] = None

class ToolCallReq(BaseModel):
    tool_name: str
    payload: dict


# ------------------------
# Tool logic
# ------------------------
def run_tool(tool_name: str, payload: dict):
    try:
        if tool_name == "get_customer":
            customer = db_utils.get_customer(DB_FILE, payload["customer_id"])
            return {"status": "ok", "customer": customer}

        elif tool_name == "list_customers":
            customers = db_utils.list_customers(
                DB_FILE,
                status=payload.get("status"),
                tier=payload.get("tier"),
                limit=payload.get("limit")
            )
            return {"status": "ok", "customers": customers}

        elif tool_name == "update_customer":
            customer = db_utils.update_customer(
                DB_FILE,
                payload["customer_id"],
                payload["data"]
            )
            return {"status": "ok", "customer": customer}

        elif tool_name == "create_ticket":
            ticket = db_utils.create_ticket(
                DB_FILE,
                payload["customer_id"],
                payload["issue"],
                payload["priority"]
            )
            return {"status": "ok", "ticket": ticket}

        elif tool_name == "get_customer_history":
            history = db_utils.get_customer_history(DB_FILE, payload["customer_id"])
            return {"status": "ok", "history": history}

        elif tool_name == "list_tickets":
            tickets = db_utils.list_tickets_for_customers(
                DB_FILE,
                payload["customer_ids"],
                status=payload.get("status"),
                priority=payload.get("priority")
            )
            return {"status": "ok", "tickets": tickets}

        elif tool_name == "reset_db":
            script_path = os.path.join(os.path.dirname(__file__), "database_setup.py")
            subprocess.run(["python", script_path], input=b"y\ny\n")
            return {"status": "ok", "message": "Database reset completed"}

        else:
            return {"status": "error", "error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ------------------------
# Streaming helpers
# ------------------------
async def stream_list(items: list):
    for item in items:
        yield f"data: {json.dumps(item)}\n\n"
        await asyncio.sleep(0.05)
    yield "event: end\ndata: done\n\n"


async def stream_customer_history(customer_id: int) -> AsyncGenerator[str, None]:
    history = db_utils.get_customer_history(DB_FILE, customer_id)
    return stream_list(history)


async def stream_list_customers(status: Optional[str], tier: Optional[str], limit: Optional[int]) -> AsyncGenerator[str, None]:
    customers = db_utils.list_customers(DB_FILE, status=status, tier=tier, limit=limit)
    return stream_list(customers)


async def stream_list_tickets(customer_ids: List[int], status: Optional[str], priority: Optional[str]) -> AsyncGenerator[str, None]:
    tickets = db_utils.list_tickets_for_customers(DB_FILE, customer_ids, status=status, priority=priority)
    return stream_list(tickets)


# ------------------------
# Streaming endpoints
# ------------------------
@app.get("/tool/get_customer_history/stream")
async def get_customer_history_stream(customer_id: int):
    return StreamingResponse(stream_customer_history(customer_id), media_type="text/event-stream")


@app.get("/tool/list_customers/stream")
async def list_customers_stream(status: Optional[str] = None, tier: Optional[str] = None, limit: Optional[int] = None):
    return StreamingResponse(stream_list_customers(status, tier, limit), media_type="text/event-stream")


@app.get("/tool/list_tickets/stream")
async def list_tickets_stream(customer_ids: List[int], status: Optional[str] = None, priority: Optional[str] = None):
    return StreamingResponse(stream_list_tickets(customer_ids, status, priority), media_type="text/event-stream")


# ------------------------
# Standard endpoints for tools
# ------------------------
@app.get("/tools/list")
def list_tools():
    return {"tools": AGENT_INFO["tools"]}


@app.post("/tools/call")
def call_tool(req: ToolCallReq):
    log_msg(f"Tool call received via /tools/call: {req.json()}")
    return run_tool(req.tool_name, req.payload)


# ------------------------
# Per-tool endpoint for AgentConnector.invoke_tool
# ------------------------
@app.post("/tool/{tool_name}")
def tool_endpoint(tool_name: str, payload: dict = Body(...)):
    log_msg(f"Tool call via /tool/{tool_name} with payload: {payload}")
    return run_tool(tool_name, payload)
'''