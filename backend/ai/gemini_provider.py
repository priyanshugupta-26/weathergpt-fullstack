from google import genai
from google.genai import types
from .base import AIResult, LLMProvider
from .prompts import SYSTEM_PROMPT, messages


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, key, model="", timeout=20):
        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=int(timeout * 1000), retry_options=types.HttpRetryOptions(attempts=2)))
        self.model = model

    async def resolve_model(self):
        if not self.model:
            available = []
            async for model in await self.client.aio.models.list():
                name = model.name or ""
                if "generateContent" in (model.supported_actions or []) and "gemini" in name:
                    if not any(x in name for x in ("image", "audio", "preview", "live", "embedding")):
                        available.append(name)
            preferred = [m for m in available if "flash" in m]
            if not available:
                raise RuntimeError("No suitable text model available")
            self.model = sorted(preferred or available)[-1]
        return self.model

    def config(self):
        return types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                           temperature=0.2, max_output_tokens=1200)

    async def generate(self, context):
        result = await self.client.aio.models.generate_content(
            model=await self.resolve_model(), contents=messages(context)[1]["content"],
            config=self.config())
        if not result.text:
            raise ValueError("Empty completion")
        usage = result.usage_metadata.model_dump() if result.usage_metadata else {}
        return AIResult(result.text, self.name, self.model, usage)

    async def stream(self, context):
        response = await self.client.aio.models.generate_content_stream(
            model=await self.resolve_model(), contents=messages(context)[1]["content"],
            config=self.config())
        async for chunk in response:
            if chunk.text:
                yield chunk.text

    async def health_check(self):
        await self.client.aio.models.get(model=await self.resolve_model())
        return {"healthy": True, "model": self.model}

    async def close(self):
        await self.client.aio.aclose()
