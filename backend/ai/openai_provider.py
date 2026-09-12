import httpx
from .base import AIResult, LLMProvider
from .prompts import messages


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4.1-mini", timeout: float = 20):
        self.key = key
        self.base_url = base_url.rstrip("/")
        self.model = model or "gpt-4.1-mini"
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
            timeout=self.timeout,
        )

    async def generate(self, context: dict) -> AIResult:
        payload = {
            "model": self.model,
            "messages": messages(context),
            "temperature": 0.3,
            "max_tokens": 1000,
        }
        res = await self.client.post("/chat/completions", json=payload)
        res.raise_for_status()
        data = res.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return AIResult(content, self.name, self.model, usage)

    async def stream(self, context: dict):
        res = await self.generate(context)
        yield res.text

    async def health_check(self) -> dict:
        return {"healthy": bool(self.key), "model": self.model}

    async def close(self):
        await self.client.aclose()
