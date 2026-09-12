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
    "binary_search_python": "Here is the implementation of Binary Search in Python:\n\n```python\ndef binary_search(arr, target):\n    low = 0\n    high = len(arr) - 1\n    \n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid  # Target found at index mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n            \n    return -1  # Target not found\n\n# Example usage:\nnumbers = [1, 3, 5, 7, 9, 11, 13]\nresult = binary_search(numbers, 7)\nprint(f\"Target found at index: {result}\")  # Output: 3\n```",
    "albert_einstein": "Albert Einstein (1879–1955) was a German-born theoretical physicist widely acknowledged as one of the greatest and most influential physicists of all time. He is best known for developing the theory of relativity, and he also made fundamental contributions to quantum mechanics. He received the 1921 Nobel Prize in Physics for his explanation of the photoelectric effect.",
    "joke": "Why do programmers prefer dark mode?\n\nBecause light attracts bugs! 😄",
    "what_is_humidity": "Humidity refers to the concentration of water vapor present in the air. Absolute humidity is the total mass of water vapor in a given volume of air, while relative humidity (expressed as a percentage) measures the current amount of water vapor relative to the maximum amount the air can hold at that specific temperature.",
    "what_is_rainfall": "Rainfall is liquid precipitation that forms when water vapor in the atmosphere cools, condenses around microscopic airborne particles (condensation nuclei) into cloud droplets, and collides to become heavy enough to fall to Earth under gravity.",
    "explain_cyclones": "A cyclone is a large-scale system of air masses that rotates around a strong center of low atmospheric pressure. They are characterized by inward-spiraling winds that rotate counterclockwise in the Northern Hemisphere and clockwise in the Southern Hemisphere. Tropical cyclones form over warm ocean waters when moist air rises rapidly, creating an intense low-pressure vortex.",
    "what_is_aqi": "The Air Quality Index (AQI) is a standardized metric used by government agencies to communicate how clean or polluted the ambient air currently is, and what associated health effects might be of concern for the public. It typically tracks pollutants such as PM2.5, PM10, ground-level ozone, nitrogen dioxide, and sulfur dioxide.",
    "what_is_farming": "Farming (agriculture) is the science, art, and practice of cultivating soil, growing crops, and raising livestock to provide food, fiber, medicinal plants, and other products to sustain and enhance human life.",
    "greeting_default": "Hi! 👋 I'm WeatherGPT. I can help with general questions as well as weather, forecasts, disaster alerts, farming advisories, climate information, and more. How can I help you today?",
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
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["greeting_default"], self.name, "general-deterministic-v1")
        if "how are you" in clean:
            return AIResult("I'm doing well, thank you! How can I help you today?", self.name, "general-deterministic-v1")
        if "einstein" in clean or "albert" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["albert_einstein"], self.name, "general-deterministic-v1")
        if "binary search" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["binary_search_python"], self.name, "general-deterministic-v1")
        if "joke" in clean:
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["joke"], self.name, "general-deterministic-v1")
        if "cyclone" in clean and ("what is" in clean or "explain" in clean or "define" in clean):
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["explain_cyclones"], self.name, "general-deterministic-v1")
        if "rainfall" in clean or ("what is rain" in clean):
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["what_is_rainfall"], self.name, "general-deterministic-v1")
        if "aqi" in clean and ("what is" in clean or "explain" in clean):
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["what_is_aqi"], self.name, "general-deterministic-v1")
        if "farming" in clean and ("what is" in clean or "explain" in clean):
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["what_is_farming"], self.name, "general-deterministic-v1")
        if "humidity" in clean and ("what is" in clean or "define" in clean):
            return AIResult(DETERMINISTIC_GENERAL_KNOWLEDGE["what_is_humidity"], self.name, "general-deterministic-v1")
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
