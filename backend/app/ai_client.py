import httpx

from .config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def call_ai_api(prompt: str, persona: str | None = None, system_prompt: str | None = None) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")

    system_content = system_prompt or persona
    messages = []
    if system_content:
        messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": prompt})

    url = f"{OPENAI_BASE_URL.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=20.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"AI API error {resp.status_code}: {resp.text}")
        data = resp.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"AI API response parse error: {exc}")
