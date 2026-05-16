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
  accepts FCP requests. The path is up to the operator.
- **Message** — the textual body of a single request or response. It
  MAY be plain text, Markdown, JSON, or any other text encoding. It
  carries intent in natural language; FCP imposes no schema on it.
- **Textual protocol** — a protocol in which the wire format is
  human-readable text and the semantics are conveyed by that text
  itself, not by a separate schema. FCP is a textual protocol.
- **Session** — an optional sequence of related requests between the
  same two actors that share state on the target side. The carrier
  (a cookie, a header, an opaque ID) is announced during the
  handshake. An actor without sessions is fully conformant.
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
   — who it is, what it can do, and any optional features it supports.
   This is the handshake.

Everything else is negotiated during the handshake, in text:

- **Authentication** — if the target requires it, the handshake
  describes how (e.g. "send `Authorization: Bearer <token>`, get one
  at …"). Unauthenticated requests to a protected endpoint SHOULD
  receive `401` with a textual body that points back at the handshake.
- **Streaming** — if the target supports streaming (chunked transfer,
  SSE), the handshake says so and how to opt in. Clients that don't
  speak streaming still get a complete response.
- **Sessions** — if the target keeps state, the handshake names the
  cookie (or header) and the client echoes it on subsequent requests.
  Stateless actors omit this entirely.
- **Anything else** — tool calling, structured output, multi-step
  tasks, preferred formats — same rule: announced in the handshake,
  agreed in text, no out-of-band schema.

## Example: booking a flight

Target actor at `https://flights.example.com`.

### Handshake

```http
GET / HTTP/1.1
Host: flights.example.com
```

```http
HTTP/1.1 200 OK
Content-Type: text/markdown

# FlightBot
I can search for and book commercial flights.
- Search by origin, destination, date — open to anyone.
- Book a flight — requires `Authorization: Bearer <token>`.
  Get a token by signing up at https://flights.example.com/signup,
  or, if you already have an account, by POSTing
  `{"email": "...", "password": "..."}` to
  https://flights.example.com/auth.
- Cancel a booking by reference — same token.

Talk to me in plain text, or POST JSON `{"message": "..."}`.
I maintain session state via the `fcp_session` cookie.
```

### Request

```http
POST / HTTP/1.1
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
`Authorization: Bearer <token>` header — see the handshake at
`GET /` for how to obtain one.
```

### Booking

```http
POST / HTTP/1.1
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

## Operational notes (informal)

These are not part of the protocol. They are reminders for anyone
deploying an FCP endpoint, because the endpoint is public by design
and the handshake invites strangers to talk to it.

- **Rate limiting.** A bare FCP endpoint is a free conversational
  API. Without limits, a single client can drive cost (compute, LLM
  tokens, downstream calls) arbitrarily high. Put per-IP, per-token,
  or per-session limits in front.
- **Body size.** Free-form text means clients can POST megabytes of
  it. Cap request bodies at a sane size (a few hundred KB is plenty
  for almost any natural-language exchange) and return `413` above
  that.
- **DoS and abuse.** The endpoint is reachable by anyone on the
  internet. Stand it up behind a firewall, WAF, or CDN with standard
  DDoS protection. Treat `GET` on the endpoint (the handshake) as
  cache-friendly; treat `POST` as expensive.
- **Prompt injection.** Because the body is unstructured text fed to
  an LLM, hostile inputs can try to redirect the actor. Apply the
  same defences you would to any AI-facing surface: sandboxed tool
  scopes, allowlists for outbound actions, human-in-the-loop for
  high-impact operations.
- **Auth before side effects.** Anything that costs money, leaks
  data, or mutates state should sit behind authentication declared
  in the handshake. Keep the handshake itself open so clients can
  learn how to authenticate.
- **Logging and observability.** Log requests and responses (with
  PII handling appropriate to your jurisdiction). Without logs an
  FCP endpoint is essentially un-debuggable, since the contract is
  the conversation.
- **Pay-per-request via agent payment protocols.** Because the
  endpoint is plain HTTP, it composes naturally with agent-to-agent
  payment schemes such as [x402](https://www.x402.org) (HTTP `402
  Payment Required` + a stablecoin settlement header). Charging
  even a tiny fee per `POST` — fractions of a cent — flips the
  economics: legitimate clients barely notice, but a flood of
  abusive requests becomes expensive enough to be self-limiting.
  The handshake is the natural place to advertise the price and
  the accepted payment rails.

None of this is mandated by FCP. The protocol stays minimal; the
operator chooses how much protection to wrap around it.
