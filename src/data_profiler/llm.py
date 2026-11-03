"""The language model: a prompt answered in the form of a JSON schema, by a model run locally.

A `LanguageModel` answers a prompt with JSON text that a schema constrains, so that its answer is
parsed, not read: the caller gives the schema, and parses the answer by it. `Ollama` is the first, a
model run by Ollama, asked without thinking - a small model thinking took minutes for one word and
found it no better - and at temperature 0, so that the same prompt is answered the same. A prompt
holds values of the database, as the samples show them: Ollama is reached past every proxy the
variables of the process name, as a proxy would take them off the machine, and a prompt and its
answer are logged at debug alone. A failure is told by the model, its endpoint and what was done.
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Final
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

_logger = logging.getLogger(__name__)

# The seconds an answer may take: a small model on the CPU of a notebook takes some for one.
_TIMEOUT: Final = 600


class LanguageModelError(Exception):
    """A failure of the language model: the model by its name and endpoint, and what was done."""


class LanguageModel(ABC):
    """A language model that answers a prompt in the form of a JSON schema.

    Attributes:
        name: The model, as its server names it.
    """

    def __init__(self, name: str) -> None:
        """Takes the name of the model."""
        self.name: Final = name

    @abstractmethod
    def answer(self, prompt: str, form: Mapping[str, object]) -> str:
        """The answer of the model to `prompt`, as JSON text that the schema `form` constrains.

        Args:
            prompt: What the model is asked.
            form: The JSON schema of the answer.

        Returns:
            The answer, as JSON text, for the caller to parse by `form`.

        Raises:
            LanguageModelError: The model cannot be reached, is not there, or fails to answer.
        """


class Ollama(LanguageModel):
    """A model run by Ollama, reached past every proxy, without thinking, at temperature 0."""

    def __init__(self, url: str, name: str) -> None:
        """Takes where Ollama answers, as `http://host:port`, and the name of the model."""
        super().__init__(name)
        self._endpoint: Final = url.rstrip("/")
        # No proxy at all, whatever the variables of the process name: a prompt holds values.
        self._opener: Final = build_opener(ProxyHandler({}))

    def answer(self, prompt: str, form: Mapping[str, object]) -> str:
        """The answer of the model to `prompt`, as JSON text that the schema `form` constrains.

        Args:
            prompt: What the model is asked.
            form: The JSON schema of the answer, given to Ollama as its `format`.

        Returns:
            The answer, as JSON text, for the caller to parse by `form`.

        Raises:
            LanguageModelError: The URL is none of Ollama, Ollama cannot be reached, does not
                have the model, fails to answer, or answers no message.
        """
        body = {
            "model": self.name,
            "messages": [{"role": "user", "content": prompt}],
            "format": form,
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        }
        _logger.debug("Asking %s: %s", self.name, prompt)
        try:
            request = Request(
                f"{self._endpoint}/api/chat",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with self._opener.open(request, timeout=_TIMEOUT) as response:
                reply = json.loads(response.read())
        except HTTPError as error:
            raise LanguageModelError(
                f"Ollama at {self._endpoint} fails to answer by the model {self.name}:"
                f" {_problem(error)}"
            ) from error
        except (URLError, OSError) as error:
            reason = error.reason if isinstance(error, URLError) else error
            raise LanguageModelError(
                f"Ollama at {self._endpoint} cannot be reached: {reason}"
            ) from error
        except json.JSONDecodeError as error:
            raise LanguageModelError(f"Ollama at {self._endpoint} answers no JSON") from error
        except ValueError as error:
            raise LanguageModelError(f"{self._endpoint} is no URL of Ollama") from error
        message = reply.get("message") if isinstance(reply, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise LanguageModelError(
                f"Ollama at {self._endpoint} answers no message of {self.name}"
            )
        _logger.debug("Answered by %s: %s", self.name, content)
        return content


def _problem(error: HTTPError) -> str:
    """What Ollama says is wrong, in the body of `error`, else its status."""
    try:
        said = json.loads(error.read()).get("error")
    except (OSError, ValueError, AttributeError):
        said = None
    return said if isinstance(said, str) else f"status {error.code}"
