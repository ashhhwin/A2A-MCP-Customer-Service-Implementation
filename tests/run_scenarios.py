import requests
import json
import time

ROUTER_URL = "http://127.0.0.1:8100/query"  # Router endpoint

# Define test scenarios
scenarios = [
    {
        "name": "Simple Query",
        "payload": {"text": "Get customer information for ID 1", "customer_id": 1, "intent": "get_customer_info"}
    },
    {
        "name": "Coordinated Query",
        "payload": {"text": "I'm customer 12345 and need help upgrading my account", "customer_id": 12345, "intent": "upgrade_request"}
    },
    {
        "name": "Complex Query",
        "payload": {"text": "Show me all active customers who have open tickets", "customer_id": 1, "intent": "list_customers"}
    },
    {
        "name": "Escalation",
        "payload": {"text": "I've been charged twice, please refund immediately!", "customer_id": 1, "intent": "refund_request"}
    },
    {
        "name": "Update Email",
        "payload": {"text": "Update my email to new@email.com", "customer_id": 1, "intent": "update_customer", "update_fields": {"email": "new@email.com"}}
    },
    {
        "name": "Show Ticket History",
        "payload": {"text": "Show my ticket history", "customer_id": 1, "intent": "get_customer_history"}
    }
]

def run_scenario(name: str, payload: dict):
    print(f"\n=== Running scenario: {name} ===")
    try:
        # Added a small timer to see performance
        start_time = time.time()
        # Increased timeout to 30s to allow for full agent-to-agent + MCP subprocess roundtrip
        response = requests.post(ROUTER_URL, json=payload, timeout=30)
        duration = time.time() - start_time
        
        if response.ok:
            data = response.json()
            print(f"Success ({duration:.2f}s):")
            print(json.dumps(data, indent=4))
        else:
            print(f"HTTP {response.status_code}: {response.text}")
    except requests.exceptions.Timeout:
        print("Request timed out. Check: Is the Customer Data Agent running? Is the MCP server working?")
    except requests.exceptions.ConnectionError:
        print("Connection error. Is the router running?")
    except Exception as e:
        print(f"Unexpected exception: {e}")

if __name__ == "__main__":
    # Ensure dependencies are ready
    print("Starting Test Scenarios...")
    for scenario in scenarios:
        run_scenario(scenario["name"], scenario["payload"])
                
'''
import requests
import json

ROUTER_URL = "http://127.0.0.1:8100/query"  # Router endpoint

# Define test scenarios
scenarios = [
    {
        "name": "Simple Query",
        "payload": {"text": "Get customer information for ID 1", "customer_id": 1, "intent": "get_customer_info"}
    },
    {
        "name": "Coordinated Query",
        "payload": {"text": "I'm customer 12345 and need help upgrading my account", "customer_id": 12345, "intent": "upgrade_request"}
    },
    {
        "name": "Complex Query",
        "payload": {"text": "Show me all active customers who have open tickets", "customer_id": 1, "intent": "list_customers"}
    },
    {
        "name": "Escalation",
        "payload": {"text": "I've been charged twice, please refund immediately!", "customer_id": 1, "intent": "refund_request"}
    },
    {
        "name": "Update Email",
        "payload": {"text": "Update my email to new@email.com", "customer_id": 1, "intent": "update_customer", "update_fields": {"email": "new@email.com"}}
    },
    {
        "name": "Show Ticket History",
        "payload": {"text": "Show my ticket history", "customer_id": 1, "intent": "get_customer_history"}
    }
]

def run_scenario(name: str, payload: dict):
    print(f"\n=== Running scenario: {name} ===")
    try:
        response = requests.post(ROUTER_URL, json=payload, timeout=10)
        if response.ok:
            data = response.json()
            print(json.dumps(data, indent=4))
        else:
            print(f"HTTP {response.status_code}: {response.text}")
    except requests.exceptions.Timeout:
        print("Request timed out.")
    except requests.exceptions.ConnectionError:
        print("Connection error. Is the router running?")
    except Exception as e:
        print(f"Unexpected exception: {e}")

if __name__ == "__main__":
    for scenario in scenarios:
        run_scenario(scenario["name"], scenario["payload"])
    '''