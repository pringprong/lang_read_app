"""OpenAI-compatible chat client (sentence generation + translation, §9).

Works with LM Studio, Alibaba Cloud (DashScope-compatible mode), and any
other OpenAI-compatible endpoint by pointing `base_url` at it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    model: str
    api_key: str | None = None
    temperature: float = 0.7
    timeout: float = 300.0  # local reasoning models can be slow


class LlmError(Exception):
    """Any failure talking to (or parsing a response from) the model."""


_JSON_FIXUP = "\n\nIMPORTANT: Reply with ONLY valid JSON. No explanations, no markdown."


def extract_json(text: str) -> Any:
    """Defensively extract the first JSON value from a model reply.

    Handles: pure JSON, ```json fenced blocks, JSON embedded in prose.
    """
    stripped = text.strip()
    # 1) direct parse
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # 2) fenced block ```json ... ``` or ``` ... ```
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", stripped, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    # 3) first balanced {...} or [...] block anywhere in the text
    #    (whichever opener appears earliest)
    starts = [(stripped.find(opener), closer)
              for opener, closer in (("{", "}"), ("[", "]"))]
    starts = [(pos, closer) for pos, closer in starts if pos != -1]
    starts.sort()
    for start, closer in starts:
        opener = stripped[start]
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    candidate = stripped[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break
    raise LlmError(f"could not extract JSON from model reply: {text[:200]!r}")


class LlmClient:
    def __init__(self, config: LlmConfig) -> None:
        self._config = config
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "not-set",  # LM Studio ignores the key
            timeout=config.timeout,
            max_retries=1,
        )

    def chat(self, prompt: str, *, system: str | None = None,
             temperature: float | None = None) -> str:
        """Send one prompt; return the reply text.

        Retries up to twice on an empty message — local reasoning models
        (e.g. Qwen 'thinking' variants) occasionally return empty content
        after producing only internal reasoning.
        """
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        reasoning_seen = False
        for attempt in range(3):  # initial attempt + 2 retries
            try:
                response = self._client.chat.completions.create(
                    model=self._config.model,
                    messages=messages,
                    temperature=self._config.temperature if temperature is None else temperature,
                )
            except Exception as exc:  # network, auth, model-not-found, timeout…
                raise LlmError(f"chat request failed: {exc}") from exc
            try:
                message = response.choices[0].message
                content = getattr(message, "content", None)
            except (AttributeError, IndexError) as exc:
                raise LlmError(f"unexpected response shape: {response!r}") from exc
            if content and content.strip():
                return content.strip()
            # empty content: note whether the model emitted reasoning instead
            reasoning = getattr(message, "reasoning_content", None) or ""
            if isinstance(reasoning, str) and reasoning.strip():
                reasoning_seen = True

        hint = ""
        if reasoning_seen:
            hint = (
                " — the model produced only internal 'reasoning' with no "
                "answer. Disable thinking/reasoning mode for this model in "
                "LM Studio, or use a non-reasoning model."
            )
        raise LlmError(f"model returned an empty message{hint}")

    def chat_json(self, prompt: str, *, system: str | None = None) -> Any:
        """Send one prompt and parse a JSON reply.

        Retries once with a 'JSON only' fix-up instruction if parsing fails.
        """
        try:
            return extract_json(self.chat(prompt, system=system))
        except LlmError:
            return extract_json(self.chat(prompt + _JSON_FIXUP, system=system))
