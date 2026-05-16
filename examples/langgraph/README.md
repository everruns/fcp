# TableBot FCP LangGraph Example

This is a minimal Free Communication Protocol endpoint implemented with
FastAPI, LangGraph, and OpenAI. The actor is `TableBot`, a demo restaurant
booking agent for The Example Table.

It exposes one FCP endpoint at `/`:

- `GET /` returns a text/Markdown handshake.
- `POST /` accepts plain natural-language text.
- Sessions are stored in LangGraph memory and keyed by the `fcp_session`
  cookie.
- Availability is public.
- Booking requires `Authorization: Demo <your name>`.
- The actor negotiates missing booking details over multiple turns and asks for
  confirmation before returning a fake booking reference.

## Run

Set `OPENAI_API_KEY` in your environment, then run:

```bash
cd examples/langgraph
uv run uvicorn app:app --reload
```

The model defaults to `gpt-5.5`. Override it with `OPENAI_MODEL`:

```bash
OPENAI_MODEL=gpt-5.5 uv run uvicorn app:app --reload
```

## Try It

```bash
curl -i http://127.0.0.1:8000/
```

```bash
curl -i -c cookies.txt \
  -H 'Content-Type: text/plain' \
  --data 'Do you have tables tomorrow around 7pm for 4?' \
  http://127.0.0.1:8000/
```

```bash
curl -i -b cookies.txt \
  -H 'Content-Type: text/plain' \
  -H 'Authorization: Demo Alice' \
  --data 'Book 7:15 tomorrow for 4.' \
  http://127.0.0.1:8000/
```

```bash
curl -i -b cookies.txt \
  -H 'Content-Type: text/plain' \
  -H 'Authorization: Demo Alice' \
  --data 'Confirm booking.' \
  http://127.0.0.1:8000/
```

The server also tolerates textual JSON bodies for clients that already send
them, but the example protocol is plain text first.
