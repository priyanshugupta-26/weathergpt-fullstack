from .base import AIResult, LLMProvider


class DeterministicWeatherProvider(LLMProvider):
    name = "deterministic"

    async def generate(self, context):
        return AIResult(context["fallback"], self.name, "weather-rules-v2")

    async def stream(self, context):
        yield context["fallback"]

    async def health_check(self):
        return {"healthy": True, "model": "weather-rules-v2"}
