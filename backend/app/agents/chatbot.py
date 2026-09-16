import json
from openai import OpenAI
from app.agents.config import settings
from app.agents.ledger_agent import (
    get_overdue_invoices,
    get_upcoming_invoices,
    get_client_ledger,
    get_invoice,
    list_clients,
)

_llm_client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

_TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "get_overdue_invoices",
        "description": "List every overdue, unpaid invoice for this business.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_upcoming_invoices",
        "description": "List invoices due in the next 3 days for this business.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_client_ledger",
        "description": "Get the full ledger history for a specific client, given their client_id.",
        "parameters": {"type": "object", "properties": {"client_id": {"type": "string"}}, "required": ["client_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_invoice",
        "description": "Get a single invoice's details and status by invoice_id.",
        "parameters": {"type": "object", "properties": {"invoice_id": {"type": "string"}}, "required": ["invoice_id"]},
    }},
        {"type": "function", "function": {
        "name": "list_clients",
        "description": "List all clients for this business with their id and name. Use this first if you need a client_id but only have a client's name.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]


def _execute_tool(name: str, args: dict, business_id: str) -> str:

    if name == "get_overdue_invoices":
        result = get_overdue_invoices.invoke({"business_id": business_id})
    elif name == "get_upcoming_invoices":
        result = get_upcoming_invoices.invoke({"business_id": business_id})
    elif name == "get_client_ledger":
        result = get_client_ledger.invoke({"client_id": args["client_id"]})
    elif name == "get_invoice":
        result = get_invoice.invoke({"invoice_id": args["invoice_id"]})
    elif name == "list_clients":
        result = list_clients.invoke({"business_id": business_id})
    else:
        result = {"error": f"Unknown tool {name}"}
    return json.dumps(result, default=str)


def answer_query(business_id: str, question: str) -> str:
    messages = [
        {"role": "system", "content": (
            "You are the Bharosa owner's assistant. Answer questions about "
            "their invoices, clients, and ledger using the tools available. "
            "Only discuss this business's own data. Be concise. "
            "Reply in plain conversational text only -- no Markdown, no "
            "tables, no bullet points, no bold/italic formatting, since "
            "your response is shown in a plain chat bubble that can't "
            "render any of that."
        )},
        {"role": "user", "content": question},
    ]

    for _ in range(3):
        response = _llm_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=_TOOLS_SCHEMA,
            temperature=0,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            return message.content or "I couldn't find an answer to that."

        messages.append(message)
        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            result = _execute_tool(tool_call.function.name, args, business_id)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

    return "I wasn't able to fully answer that -- try rephrasing or being more specific."