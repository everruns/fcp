# FCP — Free Communication Protocol

## Abstract

FCP is a minimal, text-first protocol for communication between two
parties over HTTP. It is deliberately not framed as an "agent protocol":
the parties are simply *actors*, and one actor talks to another by
sending text and reading text back.

FCP makes one assumption: both actors can understand free-form text.
Modern AI systems already can, and humans always could, so no schema,
SDK, or code generation is needed. Capability handshake, parameter
collection, and error handling happen in natural language — the same
way a person would ask a service what it does.

Existing agent-to-agent protocols (e.g. Google A2A) prescribe rich
envelopes, task lifecycles, and capability manifests. FCP rejects that
complexity: two actors that can read and write text can already
negotiate everything they need at runtime. This document is therefore
intentionally short.

## Glossary

- **Actor** — any participant that can send and receive HTTP requests
  containing text. An actor may be a software agent, a service, a
  script, or a human with `curl`. FCP does not distinguish between
  them. The actor that initiates a request is the *client actor*; the
  one that receives it is the *target actor*. Roles may swap freely
  across requests.
- **FCP endpoint** — an HTTP(S) URL operated by a target actor that
  accepts FCP requests. Conventionally `/fcp`, but any path works.
- **Message** — the textual body of a single request or response. It
  MAY be plain text, Markdown, JSON, or any other text encoding. It
  carries intent in natural language; FCP imposes no schema on it.
- **Textual protocol** — a protocol in which the wire format is
  human-readable text and the semantics are conveyed by that text
  itself, not by a separate schema. FCP is a textual protocol.
- **Session** — an optional sequence of related requests between the
  same two actors that share state on the target side. Sessions are
  carried by an HTTP cookie. An actor without sessions is fully
  conformant.
- **Handshake** — the (optional) first exchange in which the client
  actor asks the target actor what it can do, and the target replies
  in text.

## Requirements

A conformant target actor MUST:

1. Expose an HTTP(S) endpoint.
2. Accept `POST` requests whose body is text. The body MAY be JSON or
   any other text format; the actor MUST also accept plain natural
   language. If the body parses as JSON, it MAY be interpreted as
   such; otherwise it MUST be treated as text.
3. Respond with a textual body (`text/plain`, `text/markdown`, or
   `application/json` are all fine).

A conformant target actor SHOULD:

4. Respond to `GET` on the same endpoint with a textual self-description
   — who it is, what it can do, and any optional features it supports
   (auth, sessions, preferred formats). This is the handshake entry
   point.

A conformant target actor MAY:

- **Use cookies for session state.** Set a cookie on any response; the
  client SHOULD echo it on subsequent requests. Sessions are optional
  and stateless actors are fully conformant.
- **Require authentication** via any standard HTTP mechanism
  (`Authorization` header, bearer token, mTLS, etc.). Unauthenticated
  requests SHOULD receive `401` with a textual body explaining how to
  authenticate.
- **Stream** responses using chunked transfer or SSE.

That is the entire protocol. Anything else — tool calling, structured
output, multi-step tasks — is negotiated in text between the two
actors at runtime.

## Example: booking a flight

Target actor at `https://flights.example.com/fcp`.

### Handshake

```http
GET /fcp HTTP/1.1
Host: flights.example.com
```

```http
HTTP/1.1 200 OK
Content-Type: text/markdown

# FlightBot
I can search for and book commercial flights.
- Search by origin, destination, date.
- Book a flight (requires `Authorization: Bearer <token>`).
- Cancel a booking by reference.

Talk to me in plain text, or POST JSON `{"message": "..."}`.
I maintain session state via the `fcp_session` cookie.
```

### Request

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

3 options for BER → LIS on Fri 22 May 2026:
1. TAP TP535, 07:40 → 10:05, €142
2. Ryanair FR8821, 09:15 → 11:35, €98
3. Lufthansa LH1178, 10:50 → 13:20, €189

Reply with a number to book. Booking needs an
`Authorization: Bearer <token>` header.
```

### Booking

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

Booked. Reference **R7K2-Q9X**. Ryanair FR8821,
Fri 22 May 2026, 09:15 BER → 11:35 LIS, Jane Doe.
Charged €98.00. Reply "cancel R7K2-Q9X" within 24h
for a full refund.
```

No schema, no SDK, no code generation. Either actor may be an AI, a
script, or a human.
