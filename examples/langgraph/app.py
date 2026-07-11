from __future__ import annotations

import json
import os
import re
import uuid
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, Request
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from starlette.responses import PlainTextResponse


SESSION_COOKIE = "fcp_session"
MAX_BODY_BYTES = 256 * 1024
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
DEMO_AUTH_PATTERN = re.compile(r"^Demo\s+(.{1,80})$")

SYSTEM_PROMPT = """You are TableBot, an FCP restaurant booking actor for a demo
restaurant called The Example Table.

You communicate over the Free Communication Protocol: plain, useful text in;
plain, useful text out. The client actor may know nothing about you at first,
so negotiate usage in natural language.

Capabilities:
- Describe The Example Table.
- Share public demo availability.
- Negotiate a table booking over multiple turns.
- Create a demo booking only after authentication and explicit confirmation.

Authentication:
- Booking requires `Authorization: Demo <your name>`.
- Availability and general restaurant information do not require auth.
- If the client tries to book without auth, explain the exact header to send.
- If auth was attempted but invalid, explain the exact header format.
- Treat the name after `Demo` as the authenticated demo identity.

Booking policy:
- Required details: date, time or acceptable time range, party size, and booking
  name. Use the authenticated demo identity as the booking name when the client
  does not provide one.
- Before creating a booking, summarize the proposed booking and ask the client
  to confirm.
- When an authenticated client confirms a complete booking, return a fake
  booking reference like `TB-1042`.
- Do not claim to contact a real restaurant or perform a real-world booking.

Demo availability:
- Today: 6:00 PM, 7:30 PM, 8:30 PM.
- Tomorrow: 6:30 PM, 7:15 PM, 8:00 PM.
- Friday: 5:45 PM, 7:00 PM, 9:00 PM.

Keep replies concise and actionable. Track the booking negotiation across turns
using the session history.
"""

HANDSHAKE = f"""# TableBot FCP LangGraph Example

I am TableBot, a demo restaurant booking actor for The Example Table.

I can:

- describe the restaurant
- show public demo table availability
- negotiate a table booking over multiple turns
- create a fake demo booking after authentication and confirmation

Booking a table requires authentication. For this demo, send:

```http
Authorization: Demo <your name>
```

Send me a `POST` request with plain text, such as:

```text
I want dinner tomorrow for 4 people around 7pm.
```

I maintain conversational session state with the `{SESSION_COOKIE}` cookie.
The cookie is created on the first `POST`; send it back on later requests to
continue the same conversation.

Useful starters:

- `What can you do?`
- `Do you have tables tomorrow around 7pm for 4?`
- `Book 7:15 tomorrow for 4.`
- `Confirm booking.`

Responses are text/Markdown. This example keeps session state in process
memory, so sessions reset when the server restarts.
"""


def _message_to_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


def _extract_message(raw_body: bytes) -> str:
    if not raw_body:
        return ""

    body_text = raw_body.decode("utf-8", errors="replace").strip()
    if not body_text:
        return ""

    try:
        parsed: Any = json.loads(body_text)
    except json.JSONDecodeError:
        return body_text

    if isinstance(parsed, str):
        return parsed

    if isinstance(parsed, dict):
        for key in ("message", "text", "body"):
            value = parsed.get(key)
            if isinstance(value, str):
                return value
        return json.dumps(parsed, ensure_ascii=False, indent=2)

    return json.dumps(parsed, ensure_ascii=False, indent=2)


def _get_or_create_session_id(request: Request) -> tuple[str, bool]:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id and SESSION_ID_PATTERN.match(session_id):
        return session_id, False
    return uuid.uuid4().hex, True


def _demo_auth_context(request: Request) -> dict[str, str | bool | None]:
    authorization = request.headers.get("authorization")
    if not authorization:
        return {"auth_name": None, "auth_attempted": False}

    match = DEMO_AUTH_PATTERN.match(authorization.strip())
    if not match:
        return {"auth_name": None, "auth_attempted": True}

    name = match.group(1).strip()
    return {"auth_name": name or None, "auth_attempted": True}


def _text_response(
    body: str,
    *,
    status_code: int = 200,
    media_type: str = "text/markdown",
    session_id: str | None = None,
    set_session_cookie: bool = False,
) -> PlainTextResponse:
    response = PlainTextResponse(body, status_code=status_code, media_type=media_type)
    if session_id and set_session_cookie:
        response.set_cookie(
            SESSION_COOKIE,
            session_id,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


@lru_cache(maxsize=1)
def _get_model() -> ChatOpenAI:
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-5.5"))


def build_graph():
    async def call_model(state: MessagesState, config: RunnableConfig):
        configurable = config.get("configurable", {})
        auth_name = configurable.get("auth_name")
        auth_attempted = configurable.get("auth_attempted", False)
        if auth_name:
            auth_context = f"Request authentication status: authenticated as {auth_name}."
        elif auth_attempted:
            auth_context = (
                "Request authentication status: authentication attempted but invalid. "
                "The valid scheme is `Authorization: Demo <your name>`."
            )
        else:
            auth_context = "Request authentication status: unauthenticated."

        response = await _get_model().ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                SystemMessage(content=auth_context),
                *state["messages"],
            ]
        )
        return {"messages": [response]}

    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")
    return workflow.compile(checkpointer=MemorySaver())


app = FastAPI(
    title="FCP LangGraph Example",
    description="A minimal Free Communication Protocol endpoint.",
)
graph = build_graph()


@app.get("/", response_class=PlainTextResponse)
async def handshake() -> PlainTextResponse:
    return PlainTextResponse(HANDSHAKE, media_type="text/markdown")


@app.post("/", response_class=PlainTextResponse)
async def fcp_endpoint(request: Request) -> PlainTextResponse:
    raw_body = await request.body()
    if len(raw_body) > MAX_BODY_BYTES:
        return PlainTextResponse(
            "Your request body is too large. Please send at most 256 KiB of text.",
            status_code=413,
            media_type="text/plain",
        )

    message = _extract_message(raw_body)
    if not message:
        return PlainTextResponse(
            "Please send a plain text message.",
            status_code=400,
            media_type="text/plain",
        )

    session_id, is_new_session = _get_or_create_session_id(request)
    auth_context = _demo_auth_context(request)
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config={
                "configurable": {
                    "thread_id": session_id,
                    **auth_context,
                }
            },
        )
    except Exception as exc:
        return _text_response(
            "I could not complete this request because the model call failed "
            f"with `{type(exc).__name__}`. Check `OPENAI_API_KEY`, model access, "
            "and account quota, then retry the same request.",
            status_code=503,
            media_type="text/plain",
            session_id=session_id,
            set_session_cookie=is_new_session,
        )

    messages = result.get("messages", [])
    reply = _message_to_text(messages[-1]) if messages else ""
    if not reply:
        reply = "I could not produce a response. Please retry."

    return _text_response(
        reply,
        session_id=session_id,
        set_session_cookie=is_new_session,
    )


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz() -> PlainTextResponse:
    return PlainTextResponse("ok", media_type="text/plain")
