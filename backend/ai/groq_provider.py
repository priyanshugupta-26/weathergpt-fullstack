from groq import AsyncGroq
from .base import AIResult, LLMProvider
from .prompts import messages


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, key, model="", timeout=20):
        self.client = AsyncGroq(api_key=key, timeout=timeout, max_retries=1)
        self.model = model

    async def resolve_model(self):
        if not self.model:
            models = (await self.client.models.list()).data
            available = [m.id for m in models if getattr(m, "active", True)
                         and not any(x in m.id.lower() for x in
                                     ("whisper", "guard", "safeguard", "tts", "orpheus"))]
            # Select only from the live catalog; prefer a low-latency general text model.
            preferred = [m for m in available if "instant" in m or "20b" in m]
            if not available:
                raise RuntimeError("No suitable text model available")
            self.model = sorted(preferred or available)[0]
        return self.model

    async def generate(self, context):
        result = await self.client.chat.completions.create(
            model=await self.resolve_model(), messages=messages(context),
            temperature=0.2, max_completion_tokens=900,
        )
        value = result.choices[0].message.content
        if not value:
            raise ValueError("Empty completion")
        return AIResult(value, self.name, self.model,
                        result.usage.model_dump() if result.usage else {})

    async def stream(self, context):
        response = await self.client.chat.completions.create(
            model=await self.resolve_model(), messages=messages(context),
            temperature=0.2, max_completion_tokens=900, stream=True,
        )
        async with response:
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

    async def health_check(self):
        await self.resolve_model()
        await self.client.models.retrieve(self.model)
        return {"healthy": True, "model": self.model}

    async def close(self):
        await self.client.close()
