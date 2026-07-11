from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

import app as app_module


def test_handshake_describes_fcp_session_cookie():
    client = TestClient(app_module.app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert app_module.SESSION_COOKIE in response.text
    assert "TableBot" in response.text
    assert "Authorization: Demo <your name>" in response.text
    assert "plain text" in response.text
    assert '{"message"' not in response.text


def test_post_accepts_text_and_reuses_cookie_session(monkeypatch):
    class FakeGraph:
        def __init__(self):
            self.thread_ids = []

        async def ainvoke(self, payload, config):
            thread_id = config["configurable"]["thread_id"]
            self.thread_ids.append(thread_id)
            return {"messages": [AIMessage(content=f"thread {thread_id}")]}

    fake_graph = FakeGraph()
    monkeypatch.setattr(app_module, "graph", fake_graph)
    client = TestClient(app_module.app)

    first = client.post("/", content="remember this", headers={"content-type": "text/plain"})
    second = client.post("/", json={"message": "what did I say?"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert app_module.SESSION_COOKIE in first.headers["set-cookie"]
    assert len(fake_graph.thread_ids) == 2
    assert fake_graph.thread_ids[0] == fake_graph.thread_ids[1]


def test_cookie_session_preserves_multiturn_messages_in_langgraph(monkeypatch):
    class FakeModel:
        def __init__(self):
            self.human_turns = []
            self.auth_contexts = []

        async def ainvoke(self, messages):
            self.auth_contexts.append(messages[1].content)
            self.human_turns.append(
                [
                    message.content
                    for message in messages
                    if isinstance(message, HumanMessage)
                ]
            )
            return AIMessage(content=f"seen {len(self.human_turns[-1])} human turns")

    fake_model = FakeModel()
    monkeypatch.setattr(app_module, "_get_model", lambda: fake_model)
    monkeypatch.setattr(app_module, "graph", app_module.build_graph())
    client = TestClient(app_module.app)

    first = client.post(
        "/",
        content="I want dinner tomorrow for 4 around 7pm.",
        headers={"content-type": "text/plain"},
    )
    second = client.post(
        "/",
        json={"message": "Book 7:15 tomorrow for 4."},
        headers={"authorization": "Demo Alice"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert fake_model.human_turns == [
        ["I want dinner tomorrow for 4 around 7pm."],
        [
            "I want dinner tomorrow for 4 around 7pm.",
            "Book 7:15 tomorrow for 4.",
        ],
    ]
    assert fake_model.auth_contexts == [
        "Request authentication status: unauthenticated.",
        "Request authentication status: authenticated as Alice.",
    ]


def test_invalid_demo_auth_header_is_explained_to_model(monkeypatch):
    class FakeModel:
        def __init__(self):
            self.auth_context = None

        async def ainvoke(self, messages):
            self.auth_context = messages[1].content
            return AIMessage(content="auth checked")

    fake_model = FakeModel()
    monkeypatch.setattr(app_module, "_get_model", lambda: fake_model)
    monkeypatch.setattr(app_module, "graph", app_module.build_graph())
    client = TestClient(app_module.app)

    response = client.post(
        "/",
        content="Book a table.",
        headers={"content-type": "text/plain", "authorization": "Bearer Alice"},
    )

    assert response.status_code == 200
    assert "authentication attempted but invalid" in fake_model.auth_context
    assert "Authorization: Demo <your name>" in fake_model.auth_context


def test_model_failure_returns_actionable_text_and_cookie(monkeypatch):
    class FailingGraph:
        async def ainvoke(self, payload, config):
            raise RuntimeError("model unavailable")

    monkeypatch.setattr(app_module, "graph", FailingGraph())
    client = TestClient(app_module.app)

    response = client.post("/", content="hello", headers={"content-type": "text/plain"})

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("text/plain")
    assert app_module.SESSION_COOKIE in response.headers["set-cookie"]
    assert "Check `OPENAI_API_KEY`, model access, and account quota" in response.text


def test_extract_message_accepts_plain_text_and_tolerates_json():
    assert app_module._extract_message(b"hello") == "hello"
    assert app_module._extract_message(b'{"message": "hello json"}') == "hello json"
    assert app_module._extract_message(b'{"text": "hello text"}') == "hello text"
