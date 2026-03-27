import os

GROQ_MODEL = "llama-3.3-70b-versatile"


def _get_client():
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except ImportError:
        return None


def stream_groq(prompt: str):
    """Stream text from Groq. Yields text chunks."""
    client = _get_client()
    if client is None:
        yield "⚠️ Groq not configured. Add GROQ_API_KEY to your .env file."
        return
    try:
        stream = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            max_tokens=1024,
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text
    except Exception as e:
        yield f"⚠️ Groq error: {e}"


def complete_groq(prompt: str) -> str:
    """Non-streaming completion from Groq."""
    client = _get_client()
    if client is None:
        return ""
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return ""


def chat_with_tools(messages: list, tools: list) -> dict:
    """Run one round of tool-use with Groq. Returns the response message dict."""
    client = _get_client()
    if client is None:
        return {}
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=1024,
        )
        return resp.choices[0].message
    except Exception as e:
        return {"content": f"⚠️ Groq error: {e}"}


def stream_groq_messages(messages: list):
    """Stream from Groq given a messages list (supports tool result messages)."""
    client = _get_client()
    if client is None:
        yield "⚠️ Groq not configured."
        return
    try:
        stream = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            stream=True,
            max_tokens=1024,
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                yield text
    except Exception as e:
        yield f"⚠️ Groq error: {e}"
