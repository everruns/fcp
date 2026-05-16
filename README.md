# fcp

Free Communication Protocol (FCP) is a minimal, text-first protocol for
communication between two actors over HTTP.

FCP is intentionally small: an actor exposes an HTTP(S) endpoint, accepts
text in a `POST` request, and responds with text. The message body carries
the intent in natural language, Markdown, JSON, or any other text format.
Capability discovery, authentication instructions, sessions, streaming, and
error recovery are negotiated in the conversation rather than through a
separate schema or SDK.

## Why

FCP is for cases where both sides can already read and write free-form text:
AI systems, scripts, services, and humans. It avoids rich envelopes, generated
clients, and fixed capability manifests when plain HTTP plus a clear textual
handshake is enough.

## Specification

The main artifact in this repository is [SPEC.md](SPEC.md). It defines the
protocol requirements, explains the optional handshake, shows an end-to-end
example, and captures operational notes for running an FCP endpoint.

Released under the [MIT License](LICENSE).
