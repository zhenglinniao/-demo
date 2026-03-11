import random
import time

from .config import AI_FAIL_RATE

DEFAULT_RESPONSES = [
    "Thanks for your message. Here's a concise reply.",
    "I hear you. Let me think and respond clearly.",
    "Understood. Here's a helpful answer.",
    "Good question. Here's a short response.",
]


def call_ai_api(prompt: str, persona: str | None = None) -> str:
    # Simulate network latency and failures.
    time.sleep(0.1)
    if random.random() < AI_FAIL_RATE:
        raise RuntimeError("Simulated AI API failure")

    prefix = f"[{persona}] " if persona else ""
    base = random.choice(DEFAULT_RESPONSES)
    return f"{prefix}{base}"
