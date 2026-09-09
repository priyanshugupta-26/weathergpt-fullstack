from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from collections.abc import AsyncIterator


@dataclass
class AIResult:
    text: str
    provider: str
    model: str = ""
    usage: dict = field(default_factory=dict)


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, context: dict) -> AIResult: ...

    @abstractmethod
    def stream(self, context: dict) -> AsyncIterator[str]: ...

    @abstractmethod
    async def health_check(self) -> dict: ...
