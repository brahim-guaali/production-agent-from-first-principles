"""A thin Gemini client: tool calls for the loop, structured output for graph nodes.

It also does the dull, necessary parts: it stays under the free tier's rate limit, retries
on 429 and 503, falls back to a lighter model when the main one is overloaded, and counts
every call and token so stages can compare cost.
"""
import os
import threading
import time
from dataclasses import dataclass, field

from google import genai
from google.genai import errors, types

MODELS = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite,gemini-3.5-flash").split(",")
RPM = float(os.environ.get("GEMINI_RPM", "8"))

# Illustrative list prices (USD per 1M tokens) to compare designs; the free tier bills nothing.
PRICE_IN, PRICE_OUT = 0.30, 2.50


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    models: dict = field(default_factory=dict)        # which model answered, and how often
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, response, seconds, model=None):
        u = response.usage_metadata
        with self._lock:
            self.calls += 1
            if model:
                self.models[model] = self.models.get(model, 0) + 1
            self.input_tokens += u.prompt_token_count or 0
            self.output_tokens += (u.candidates_token_count or 0) + (u.thoughts_token_count or 0)
            self.seconds += seconds

    @property
    def cost(self):
        return (self.input_tokens * PRICE_IN + self.output_tokens * PRICE_OUT) / 1e6

    def snapshot(self):
        return {"calls": self.calls, "models": dict(self.models), "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "cost": round(self.cost, 6)}

    def __str__(self):
        models = ", ".join(f"{n}× {m}" for m, n in self.models.items())
        return (f"{self.calls} model calls ({models}), {self.input_tokens:,} tokens in, "
                f"{self.output_tokens:,} out, ~${self.cost:.4f}")


class _RateLimiter:
    """At most RPM calls per minute across all threads."""

    def __init__(self, rpm):
        self.interval, self.next_at, self.lock = 60.0 / rpm, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            at = max(now, self.next_at)
            self.next_at = at + self.interval
        time.sleep(max(0.0, at - now))


_limiter = _RateLimiter(RPM)


class Gemini:
    def __init__(self, models=None, usage=None):
        if not os.environ.get("GEMINI_API_KEY"):
            raise SystemExit("Set GEMINI_API_KEY (free: https://aistudio.google.com/apikey).")
        self.client = genai.Client()
        self.models = models or MODELS
        self.usage = usage or Usage()

    def _generate(self, contents, config):
        """One model call with rate limiting, retries and model fallback."""
        last = None
        for attempt in range(6):
            model = self.models[min(attempt // 2, len(self.models) - 1)]
            _limiter.wait()
            t0 = time.monotonic()
            try:
                response = self.client.models.generate_content(model=model, contents=contents, config=config)
            except (errors.ServerError, errors.ClientError) as e:
                code = getattr(e, "code", None)
                if code not in (429, 500, 503) and isinstance(e, errors.ClientError):
                    raise
                last = e
                time.sleep(min(30, 2 ** attempt * 2))
                continue
            except Exception as e:  # dropped connections
                last = e
                time.sleep(2 ** attempt)
                continue
            self.usage.add(response, time.monotonic() - t0, model)
            return response
        raise RuntimeError(f"Gemini kept failing: {last}")

    def chat(self, system, contents, tools):
        """For the agent loop: the model sees the whole transcript and may call tools."""
        config = types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=tools)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            temperature=0,
        )
        return self._generate(contents, config)

    def stream(self, system, prompt, on_chunk):
        """Stream a text answer (stage 04). on_chunk(text) is called for every piece as it
        arrives; if it returns False the customer is gone, so we stop generating. Returns the
        text, time to first token, total time, number of chunks and whether it was cut off."""
        config = types.GenerateContentConfig(system_instruction=system, temperature=0.3)
        last = None
        for attempt in range(4):
            model = self.models[min(attempt // 2, len(self.models) - 1)]
            _limiter.wait()
            t0, text, chunks, ttft, final = time.monotonic(), "", 0, None, None
            try:
                stream = self.client.models.generate_content_stream(model=model, contents=prompt, config=config)
                for response in stream:
                    piece = response.text or ""
                    final = response
                    if not piece:
                        continue
                    if ttft is None:
                        ttft = time.monotonic() - t0
                    text, chunks = text + piece, chunks + 1
                    if on_chunk(piece) is False:
                        stream.close()                      # stop paying for words nobody reads
                        break
                else:
                    pass
            except (errors.ServerError, errors.ClientError) as e:
                if chunks:                                   # failed mid-stream: keep what was said
                    raise
                if getattr(e, "code", None) not in (429, 500, 503) and isinstance(e, errors.ClientError):
                    raise
                last = e
                time.sleep(min(30, 2 ** attempt * 2))
                continue
            aborted = final is None or not (final.candidates and final.candidates[0].finish_reason)
            if final is not None and final.usage_metadata:
                self.usage.add(final, time.monotonic() - t0, model)
            else:
                with self.usage._lock:
                    self.usage.calls += 1
                    self.usage.models[model] = self.usage.models.get(model, 0) + 1
            return {"text": text, "ttft": ttft, "seconds": time.monotonic() - t0, "chunks": chunks,
                    "aborted": aborted, "model": model}
        raise RuntimeError(f"Gemini kept failing: {last}")

    def structured(self, system, prompt, schema):
        """For a graph node: one narrow question in, one typed answer (a pydantic model) out."""
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0,
        )
        response = self._generate(prompt, config)
        return response.parsed if response.parsed is not None else schema.model_validate_json(response.text)
