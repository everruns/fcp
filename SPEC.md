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

- **Actor** — any participant in the communication. The actor that
  initiates a request is the *client actor*; the one that receives
  it is the *target actor*. Roles may swap freely across requests.
- **Endpoint** — an HTTP(S) URL operated by a target actor that
  accepts FCP requests. The path is up to the operator.
- **Message** — the textual body of a single request or response. It
  MAY be plain text, Markdown, JSON, or any other text encoding. It
  carries intent in natural language; FCP imposes no schema on it.
- **Protocol** — a wire format in which semantics are conveyed by
  the payload itself, not by a separate schema. FCP is text-first:
  payloads are human-readable text by default. Non-textual
  entrypoints (e.g. binary or multimodal payloads) may be supported
  later; they are negotiated the same way as everything else, via
  the handshake.
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
deploying an endpoint, because the endpoint is public by design
and the handshake invites strangers to talk to it.

- **Rate limiting.** A bare endpoint is a free conversational
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
  endpoint is essentially un-debuggable, since the contract is
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

## Unexpected situations (informal)

FCP deliberately does not lean on HTTP status codes to carry meaning.
Status codes are fine as transport signals, but the actionable part
of any response — what the client actor should do next — lives in
the textual body.

The guiding rule: **every response is actionable**. If something
went wrong, didn't go as planned, or simply requires more from the
client, the body should say so in plain text and tell the client
how to proceed. Not "error 403", but "you need to be authenticated;
get a token at https://… and try again."

Common situations and what an actionable response looks like:

- **Authorization needed.** Reply with text explaining what kind of
  authorization is required, where to obtain it (signup URL,
  OAuth flow, etc.), and what header to send next time. Pointing
  back at the handshake is fine.
- **Payment needed.** If the request is gated behind a fee, the
  response should name the price, the accepted rails (e.g. x402),
  and a link or address to settle. After payment, the client
  retries the same request.
- **Under load / rate limited.** Say so plainly: "I'm under
  pressure right now, retry in ~30 seconds" or "you've used your
  hourly quota; resets at 14:00 UTC". A `Retry-After` header is
  welcome but the body should also carry the same information in
  text.
- **Ambiguous or incomplete request.** Don't fail — ask. "I'd be
  happy to book that, but I need a passenger name and date of
  birth." A clarifying question is a perfectly normal response.
- **Capability gap.** If the client asked for something the actor
  can't do, say what *is* possible and, if relevant, point at
  another actor that can. "I only handle flights; for hotels, try
  https://hotels.example.com."
- **Internal failure.** Even genuine bugs should produce text the
  client can act on: "Something went wrong on my side, request id
  abc123, please retry in a minute or contact support@…". Avoid
  bare `500`s with no body.

The motivation is the same throughout FCP: the *conversation* is
the contract. A response that only says `401` forces the client to
guess; a response that says how to authenticate lets the client
keep going on its own.
