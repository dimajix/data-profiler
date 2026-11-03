"""Tests of the language model: Ollama asked in the form of a JSON schema, refused where amiss.

The tests that ask a model need the Ollama of the simulation environment, with the model of the
example project pulled into it.
"""

import json
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

from data_profiler.llm import LanguageModelError, Ollama
from data_profiler.project import Project

_EXAMPLE = Path(__file__).parents[1] / "examples" / "crm"

# Where the Ollama of the simulation environment answers.
_OLLAMA = "http://localhost:11434"

_FORM = {
    "type": "object",
    "properties": {"word": {"type": "string"}},
    "required": ["word"],
}


@pytest.fixture(scope="module")
def llm() -> str:
    """The language model of the example project, which the simulation environment has pulled."""
    return Project.read(_EXAMPLE, {}).llm


def test_a_model_answers_in_the_form_asked_for_past_every_proxy(
    llm: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    for variable in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
        monkeypatch.setenv(variable, "http://localhost:9")
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)
    answer = Ollama(_OLLAMA, llm).answer('Which word does "cust" stand for?', _FORM)
    assert isinstance(json.loads(answer)["word"], str), "parsed by its form"


def test_a_model_ollama_does_not_have_is_refused_naming_it() -> None:
    with pytest.raises(LanguageModelError, match="fails to answer by the model no-such-model:"):
        Ollama(_OLLAMA, "no-such-model").answer("Anything?", _FORM)


def test_an_ollama_that_cannot_be_reached_is_named() -> None:
    with pytest.raises(LanguageModelError, match=r"Ollama at http://localhost:9 cannot be reached"):
        Ollama("http://localhost:9", "any").answer("Anything?", _FORM)


class _Replying(BaseHTTPRequestHandler):
    """Answers every request with the body of its server."""

    def do_POST(self) -> None:
        """Answers with the body of the server."""
        body: bytes = self.server.body  # type: ignore[attr-defined]  # set by the fixture
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Logs nothing."""


@pytest.fixture
def replying() -> Iterator[Callable[[bytes], str]]:
    """A server on this machine that answers with the body given; its URL, once given it."""
    server = ThreadingHTTPServer(("localhost", 0), _Replying)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def replying(body: bytes) -> str:
        server.body = body  # type: ignore[attr-defined]  # read by the handler
        return f"http://localhost:{server.server_address[1]}"

    yield replying
    server.shutdown()


@pytest.mark.parametrize(
    ("body", "problem"),
    [
        (b"no JSON", "answers no JSON"),
        (b'{"message": "a text"}', "answers no message of any"),
        (b'{"message": {"content": 1}}', "answers no message of any"),
    ],
)
def test_an_answer_of_no_message_is_refused(
    replying: Callable[[bytes], str], body: bytes, problem: str
) -> None:
    with pytest.raises(LanguageModelError, match=problem):
        Ollama(replying(body), "any").answer("Anything?", _FORM)


def test_an_answer_is_the_content_of_the_message_of_ollama(
    replying: Callable[[bytes], str],
) -> None:
    url = replying(b'{"message": {"role": "assistant", "content": "{\\"word\\": \\"a\\"}"}}')
    assert Ollama(url, "any").answer("Anything?", _FORM) == '{"word": "a"}'
