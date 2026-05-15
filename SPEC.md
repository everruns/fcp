# FCP — Free Communication Protocol

## Abstract

FCP (Free Communication Protocol) is a minimal, text-first protocol for
machine-to-machine communication — primarily between autonomous agents,
but equally usable for human-to-agent or agent-to-service exchanges.

Unlike structured RPC protocols (gRPC, OpenAPI, MCP), FCP does not
prescribe a schema for what one actor can ask of another. Instead, it
assumes that both sides are capable of interpreting unstructured natural
language (or any other free-form textual content), in the same way a
human would converse with a modern AI assistant. The "API" between two
FCP actors is discovered by *asking*, not by reading a static contract.

FCP is intentionally trivial to implement: any HTTP endpoint that accepts
a POST containing text and returns text is already a valid FCP actor.

## Requirements

An FCP-compliant actor MUST satisfy the following:

1. **HTTP transport.** The actor exposes one HTTP(S) endpoint (the "FCP
   endpoint"). No specific path is mandated; `/fcp` is recommended.
2. **POST accepts free-form text.** The endpoint MUST accept HTTP `POST`
   requests whose body is textual. The body MAY be plain text, Markdown,
   JSON, or any other text representation. The actor SHOULD attempt to
   interpret the body as JSON first; if that fails, it MUST treat the
   body as natural-language text.
3. **Textual response.** The actor MUST respond with a textual body.
   `Content-Type: text/plain`, `text/markdown`, or `application/json`
   are all acceptable. The response represents the actor's answer,
   acknowledgement, or result.
4. **Self-description on GET.** The actor SHOULD respond to an HTTP
   `GET` on the same endpoint with a textual self-description: who it
   is, what it can do, and any optional capabilities (auth, session,
   tool-calling conventions) it supports. This is the entry point for
   discovery — a client with no prior knowledge can begin here.

An FCP actor MAY additionally support:

- **Sessions via cookies.** If the actor wishes to maintain conversation
  state across requests, it MAY set a `Set-Cookie` header on its
  response; clients SHOULD echo cookies back on subsequent requests.
  Sessions are entirely optional — a stateless actor is fully conformant.
- **Authentication.** Any standard HTTP auth mechanism (`Authorization`
  header, bearer tokens, mTLS, etc.) MAY be required. Unauthenticated
  requests SHOULD receive a `401` with a textual body describing how to
  authenticate.
- **Capability negotiation.** Either side MAY ask the other, in natural
  language, what it supports ("can you call tools?", "do you accept
  JSON?", "what models do you speak?"). The reply is itself just text.
- **Streaming.** Responses MAY be streamed using `Transfer-Encoding:
  chunked` or Server-Sent Events. Clients that do not support streaming
  MUST still receive a complete, well-formed response.

## Request/Response shape

There is no required schema. The following shapes are merely conventions
two actors may agree on:

- **Plain text** — body is the message; response body is the reply.
- **JSON envelope** — body is `{"message": "...", "context": {...}}`;
  response is `{"reply": "...", "actions": [...]}`. Fields are
  free-form; unknown fields MUST be ignored.

The protocol does not distinguish "questions" from "commands" from
"events" — the recipient infers intent from the text, just as a person
would.

## Discovery flow

A typical first contact between two actors:

1. Client `GET`s the FCP endpoint. Server replies with a textual
   description of who it is and what it can do.
2. Client `POST`s a natural-language request.
3. Server replies, optionally asking clarifying questions, optionally
   requesting auth, optionally setting a session cookie.
4. Conversation continues by `POST`ing further messages, echoing any
   session cookie that was set.

No step is mandatory beyond step 2 — a client that already knows what
the server does can skip discovery entirely.

## Example: booking a flight

The server is a flight-booking agent at `https://flights.example.com/fcp`.

### 1. Discovery

```http
GET /fcp HTTP/1.1
Host: flights.example.com
```

```http
HTTP/1.1 200 OK
Content-Type: text/markdown

# FlightBot

I can search for and book commercial flights. I support:

- Searching flights by origin, destination, and date.
- Booking a selected flight (requires authentication — send an
  `Authorization: Bearer <token>` header; tokens are issued at
  https://flights.example.com/auth).
- Cancelling a booking by reference number.

You can talk to me in plain English, or send JSON of the form
`{"message": "...", "passenger": {...}}`. I keep conversation state
via a session cookie (`fcp_session`).
```

### 2. First request (unauthenticated, exploratory)

```http
POST /fcp HTTP/1.1
Host: flights.example.com
Content-Type: text/plain

Find me a flight from Berlin to Lisbon next Friday morning,
one passenger, economy.
```

```http
HTTP/1.1 200 OK
Content-Type: text/markdown
Set-Cookie: fcp_session=8a1f...; Path=/; HttpOnly

I found 3 options for BER → LIS on Fri 22 May 2026:

1. TAP TP535, 07:40 → 10:05, €142
2. Ryanair FR8821, 09:15 → 11:35, €98
3. Lufthansa LH1178, 10:50 → 13:20, €189

Reply with the number to book, or ask me to refine the search.
Booking requires an `Authorization: Bearer <token>` header.
```

### 3. Booking (with auth, session cookie echoed back)

```http
POST /fcp HTTP/1.1
Host: flights.example.com
Content-Type: text/plain
Cookie: fcp_session=8a1f...
Authorization: Bearer eyJhbGciOi...

Book option 2 for Jane Doe, passport AB123456.
```

```http
HTTP/1.1 200 OK
Content-Type: text/markdown

Booked. Confirmation reference **R7K2-Q9X**. Ryanair FR8821,
Fri 22 May 2026, 09:15 BER → 11:35 LIS, Jane Doe. Total
charged: €98.00. Reply "cancel R7K2-Q9X" to cancel within
24 hours for a full refund.
```

That is the entire interaction — no schema, no SDK, no code generation.
Either side may be an AI agent, a script, or a human with `curl`.
