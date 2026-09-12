import asyncio
import time
from dataclasses import asdict
from ..config import settings
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider
from .fallback_provider import DeterministicWeatherProvider


class AIProviderRouter:
    def __init__(self, providers=None):
        self.providers = providers if providers is not None else {}
        self.injected = providers is not None
        self.signature = None
        self.metrics = {}
        self.active = "deterministic"

    async def configure(self):
        if self.injected:
            return
        sig = (settings.groq_api_key, settings.groq_model,
               settings.gemini_api_key, settings.gemini_model,
               settings.llm_api_key, settings.llm_base_url, settings.llm_model)
        if sig == self.signature:
            return
        for p in self.providers.values():
            if hasattr(p, "close"):
                await p.close()
        self.providers = {"deterministic": DeterministicWeatherProvider()}
        if settings.groq_api_key:
            self.providers["groq"] = GroqProvider(settings.groq_api_key, settings.groq_model, timeout=settings.ai_timeout)
        if settings.gemini_api_key:
            self.providers["gemini"] = GeminiProvider(settings.gemini_api_key, settings.gemini_model, timeout=settings.ai_timeout)
        if settings.llm_api_key:
            self.providers["openai"] = OpenAIProvider(settings.llm_api_key, settings.llm_base_url, settings.llm_model, timeout=settings.ai_timeout)
        self.signature = sig

    def order(self):
        names = ([settings.ai_primary_provider, settings.ai_fallback_provider]
                 if settings.ai_provider == "auto" else [settings.ai_provider])
        if settings.llm_api_key and "openai" not in names:
            names.append("openai")
        return list(dict.fromkeys(names + ["deterministic"]))

    def record(self, name, started, error=None, usage=None):
        metric = self.metrics.setdefault(name, {"requests": 0, "errors": 0,
                                               "input_tokens": 0, "output_tokens": 0})
        metric["requests"] += 1
        metric["errors"] += int(error is not None)
        metric["latency_ms"] = round((time.monotonic() - started) * 1000)
        metric["healthy"] = error is None
        metric["error"] = type(error).__name__ if error else None
        metric["checked_at"] = time.time()
        usage = usage or {}
        metric["input_tokens"] += usage.get("prompt_tokens", usage.get("prompt_token_count", 0)) or 0
        metric["output_tokens"] += usage.get("completion_tokens", usage.get("candidates_token_count", 0)) or 0

    async def generate(self, context):
        await self.configure()
        for name in self.order():
            p = self.providers.get(name)
            if not p:
                continue
            started = time.monotonic()
            try:
                result = await asyncio.wait_for(p.generate(context), settings.ai_timeout * 2)
                self.record(name, started, usage=result.usage)
                self.active = name
                return result
            except Exception as error:
                self.record(name, started, error)
        return await DeterministicWeatherProvider().generate(context)

    async def stream(self, context):
        await self.configure()
        for name in self.order():
            p = self.providers.get(name)
            if not p:
                continue
            started, emitted = time.monotonic(), False
            try:
                async with asyncio.timeout(settings.ai_timeout * 2):
                    async for token in p.stream(context):
                        if token:
                            emitted = True
                            yield {"type": "delta", "text": token, "provider": name}
                if not emitted:
                    raise ValueError("Empty completion")
                self.record(name, started)
                self.active = name
                yield {"type": "provider", "provider": name, "model": getattr(p, "model", "weather-rules-v2")}
                return
            except Exception as error:
                self.record(name, started, error)
                if emitted:
                    # Discard partial failed-provider output before replacing it.
                    yield {"type": "reset", "text": ""}
        yield {"type": "delta", "text": context["fallback"], "provider": "deterministic"}

    async def status(self, check=False):
        await self.configure()
        if check:
            async def probe(name, p):
                start = time.monotonic()
                try:
                    await asyncio.wait_for(p.health_check(), settings.ai_timeout)
                    self.record(name, start)
                except Exception as error:
                    self.record(name, start, error)
            await asyncio.gather(*(probe(n, p) for n, p in self.providers.items()))
        return {"selection": settings.ai_provider, "primary": settings.ai_primary_provider,
                "fallback": "deterministic", "secondary": settings.ai_fallback_provider,
                "active": self.active, "providers": {
                    name: {"configured": name in self.providers,
                           "status": ("Not configured" if name not in self.providers else
                                      "Error" if self.metrics.get(name, {}).get("healthy") is False else
                                      "Connected" if name in self.metrics or name == "deterministic" else "Not checked"),
                           "model": getattr(self.providers.get(name), "model", ""),
                           **self.metrics.get(name, {})}
                    for name in ("groq", "gemini", "deterministic")}}


ai_router = AIProviderRouter()
