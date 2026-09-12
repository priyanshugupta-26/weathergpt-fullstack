import re
from .base import AIResult, LLMProvider

DETERMINISTIC_GENERAL_KNOWLEDGE = {
    "capital_of_japan": "The capital of Japan is Tokyo.",
    "apj_abdul_kalam": "Dr. A.P.J. Abdul Kalam (1931–2015) was a renowned Indian aerospace scientist and statesman who served as the 11th President of India from 2002 to 2007. Widely known as the 'Missile Man of India' for his pivotal role in developing India's civilian space program and military missile capabilities, he was deeply revered as the 'People\'s President' and wrote inspiring books including *Wings of Fire*.",
    "machine_learning": "Machine learning is a field of artificial intelligence (AI) that focuses on developing algorithms and models capable of learning patterns from data to make predictions or decisions without being explicitly programmed for every scenario.",
    "recursion_python": "Recursion is a programming technique where a function calls itself to solve a smaller subproblem until it reaches a terminating base case.\n\nExample in Python:\n```python\ndef factorial(n):\n    if n <= 1:\n        return 1  # Base case\n    return n * factorial(n - 1)  # Recursive call\n\nprint(factorial(5))  # Output: 120\n```",
    "factorial_java": "Here is a Java program to calculate the factorial of a number:\n\n```java\npublic class Factorial {\n    public static long factorial(int n) {\n        if (n <= 1) return 1;\n        return n * factorial(n - 1);\n    }\n\n    public static void main(String[] args) {\n        int num = 5;\n        System.out.println(\"Factorial of \" + num + \" is: \" + factorial(num));\n    }\n}\n```",
    "linkedin_caption": "🚀 Excited to share my latest project! Innovation and continuous learning are at the heart of everything I build. Check out the project details and feel free to connect or share your thoughts!\n\n#Technology #Innovation #AI #SoftwareEngineering #Development",
    "humidity_explanation": "Humidity makes hot weather feel significantly hotter because high moisture levels in the ambient air reduce the rate of sweat evaporation from your skin. Evaporation is your body's primary physiological cooling mechanism; when it is inhibited by humid air, your body retains heat, raising the 'feels-like' temperature (heat index).",
    "what_is_python": "Python is a high-level, interpreted programming language known for its clear syntax, readability, and versatile ecosystem. It supports multiple programming paradigms (procedural, object-oriented, and functional) and is widely used across web development, data science, machine learning, and automation.",
    "reverse_string_python": "Here is how to reverse a string in Python:\n\n```python\n# Method 1: String slicing (most Pythonic)\ntext = \"hello\"\nreversed_text = text[::-1]\nprint(reversed_text)  # Output: 'olleh'\n\n# Method 2: Using reversed() and join()\nreversed_text = \"\".join(reversed(text))\nprint(reversed_text)  # Output: 'olleh'\n```",
}


class DeterministicWeatherProvider(LLMProvider):
    name = "deterministic"

    async def generate(self, context):
        fallback = context.get("fallback")
        if fallback:
            return AIResult(fallback, self.name, "weather-rules-v2")

        msg = context.get("message", "").strip().lower()
        clean = re.sub(r"[?!.,'\"]", "", msg).strip()

        # Check common greetings
        if clean in ("hi", "hello", "hey", "namaste", "vanakkam", "greetings"):
            return AIResult("Hi! How can I help you today?", self.name, "general-deterministic-v1")
        if "how are you" in clean:
            return AIResult("I'm doing well, thank you! How can I help you today?", self.name, "general-deterministic-v1")
        if "capital of japan" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["capital_of_japan"], self.name, "general-deterministic-v1")
        if "apj" in clean or "abdul kalam" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["apj_abdul_kalam"], self.name, "general-deterministic-v1")
        if "machine learning" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["machine_learning"], self.name, "general-deterministic-v1")
        if "what is python" in clean or clean == "python" or "explain python" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["what_is_python"], self.name, "general-deterministic-v1")
        if "reverse" in clean and "string" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["reverse_string_python"], self.name, "general-deterministic-v1")
        if "recursion" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["recursion_python"], self.name, "general-deterministic-v1")
        if "factorial" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["factorial_java"], self.name, "general-deterministic-v1")
        if "linkedin" in clean and "caption" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["linkedin_caption"], self.name, "general-deterministic-v1")
        if "humidity" in clean and ("feel" in clean or "hot" in clean):
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["humidity_explanation"], self.name, "general-deterministic-v1")

        default_text = (
            f"I understand your question about '{context.get('message', '')}'. "
            "To enable comprehensive open-ended conversational generation across any topic, configure an LLM provider "
            "(Groq, Gemini, or an OpenAI-compatible API key) in your `.env` file."
        )
        return AIResult(default_text, self.name, "general-deterministic-v1")

    async def stream(self, context):
        res = await self.generate(context)
        yield res.text

    async def health_check(self):
        return {"healthy": True, "model": "weather-rules-v2"}
