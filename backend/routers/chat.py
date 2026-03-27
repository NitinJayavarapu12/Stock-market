import asyncio
import json
import os
import threading
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_PROMPT = """You are a brutally honest stock market friend for a casual Indian retail investor. Think of yourself as that one friend everyone wishes they had — who actually knows the market and gives the real answer, not the safe answer.

Rules:
- Lead with the recommendation. "Sell it." / "Hold, don't panic." / "Avoid this right now." THEN explain why.
- Be blunt. If the stock looks weak, say it's weak. Don't say "it may be worth monitoring the situation."
- Talk like a WhatsApp message — short, real, no corporate tone.
- Use actual numbers in your answer. "RSI is at 74, the stock has been running hot — could pull back soon."
- Never use "bullish", "bearish", "overbought", "oversold" — say what it means in plain English instead.
- If someone says "I bought at ₹X" — calculate their P&L first using calculate_pnl, then give a direct take.
- No filler openers. No "Certainly!" No "Great question!" Just answer.
- One short disclaimer only if giving a buy/sell opinion. Not on every single message.
- Use ₹ for prices. Use % for changes.
- Keep it under 150 words unless the question genuinely needs more depth."""


class ChatRequest(BaseModel):
    message: str
    history: list = []


def _execute_tool(name: str, args: dict) -> str:
    try:
        if name == "search_stock":
            from data.fetcher import search_stocks
            results = search_stocks(args.get("query", ""), top_n=5)
            if not results:
                return "No stocks found matching that query."
            lines = [f"{r['symbol']} — {r['company']}" for r in results]
            return "\n".join(lines)

        elif name == "get_stock_data":
            from data.fetcher import fetch_stock_history
            from data.processor import get_latest_stats
            from models.indicators import get_indicator_summary
            symbol = args.get("symbol", "")
            df = fetch_stock_history(symbol)
            if df is None or df.empty:
                return f"No data found for {symbol}. Try searching for the correct symbol."
            stats = get_latest_stats(df)
            indicators = get_indicator_summary(df)
            return json.dumps({
                "symbol": symbol,
                "price": stats.get("price"),
                "day_change_pct": stats.get("day_change_pct"),
                "week_52_high": stats.get("week_52_high"),
                "week_52_low": stats.get("week_52_low"),
                "rsi": indicators.get("rsi"),
                "rsi_signal": indicators.get("rsi_signal"),
                "macd_signal": indicators.get("macd_signal"),
                "trend": indicators.get("trend"),
                "ema_20": indicators.get("ema_20"),
                "ema_50": indicators.get("ema_50"),
                "bb_position": indicators.get("bb_position"),
            })

        elif name == "get_market_summary":
            from data.fetcher import fetch_index_data, fetch_movers
            from config.settings import INDICES
            indices = {}
            for iname, isym in INDICES.items():
                d = fetch_index_data(isym)
                if d:
                    indices[iname] = d
            movers = fetch_movers()
            return json.dumps({"indices": indices, "movers": movers})

        elif name == "calculate_pnl":
            from data.fetcher import fetch_stock_history
            from data.processor import get_latest_stats
            symbol = args.get("symbol", "")
            buy_price = float(args.get("buy_price", 0))
            quantity = float(args.get("quantity", 1))
            df = fetch_stock_history(symbol)
            if df is None or df.empty:
                return f"No data found for {symbol}."
            stats = get_latest_stats(df)
            current = stats.get("price", 0)
            invested = buy_price * quantity
            current_value = current * quantity
            pnl = current_value - invested
            pnl_pct = (pnl / invested * 100) if invested else 0
            return json.dumps({
                "symbol": symbol,
                "buy_price": buy_price,
                "current_price": current,
                "quantity": quantity,
                "invested": round(invested, 2),
                "current_value": round(current_value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
            })

    except Exception as e:
        return f"Error executing {name}: {e}"

    return "Unknown tool."


def _build_tools():
    try:
        from google.genai import types
        return [types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name="search_stock",
                description="Search for an Indian stock by company name or partial symbol. Use this when the user mentions a company name like 'Infosys' or 'Tata Motors'.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"query": types.Schema(type=types.Type.STRING, description="Company name or partial symbol")},
                    required=["query"]
                )
            ),
            types.FunctionDeclaration(
                name="get_stock_data",
                description="Get current price, day change, 52-week high/low, RSI, MACD, trend and other technical indicators for a stock.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"symbol": types.Schema(type=types.Type.STRING, description="NSE symbol e.g. RELIANCE.NS, INFY.NS")},
                    required=["symbol"]
                )
            ),
            types.FunctionDeclaration(
                name="get_market_summary",
                description="Get current Indian market summary including NIFTY 50, SENSEX, NIFTY Bank, NIFTY IT indices and today's top gainers and losers.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={})
            ),
            types.FunctionDeclaration(
                name="calculate_pnl",
                description="Calculate profit or loss for a stock position. Use when user says 'I bought X shares at ₹Y' or asks if they should sell.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "symbol": types.Schema(type=types.Type.STRING, description="NSE symbol e.g. TCS.NS"),
                        "buy_price": types.Schema(type=types.Type.NUMBER, description="Price at which user bought"),
                        "quantity": types.Schema(type=types.Type.NUMBER, description="Number of shares"),
                    },
                    required=["symbol", "buy_price"]
                )
            ),
        ])]
    except Exception:
        return []


MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]


def _is_rate_limit(e):
    return "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)


def _run_groq_agent(gemini_contents, queue, loop):
    """Groq fallback agent using OpenAI-compatible tool calling."""
    try:
        from ai.groq_client import chat_with_tools, stream_groq_messages

        # Convert Gemini contents to OpenAI-style messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for c in gemini_contents:
            role = "user" if c.role == "user" else "assistant"
            text = " ".join(p.text for p in c.parts if hasattr(p, "text") and p.text)
            if text:
                messages.append({"role": role, "content": text})

        # Groq tool definitions (OpenAI format)
        groq_tools = [
            {"type": "function", "function": {"name": "search_stock", "description": "Search for an Indian stock by company name or symbol.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "get_stock_data", "description": "Get current price and technical indicators for a stock.", "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}}},
            {"type": "function", "function": {"name": "get_market_summary", "description": "Get current Indian market summary with indices and movers.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "calculate_pnl", "description": "Calculate profit/loss for a stock position.", "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}, "buy_price": {"type": "number"}, "quantity": {"type": "number"}}, "required": ["symbol", "buy_price"]}}},
        ]

        import json as _json

        MAX_ROUNDS = 5
        tool_results_summary = []

        for _ in range(MAX_ROUNDS):
            response_msg = chat_with_tools(messages, groq_tools)
            if not response_msg:
                break

            tool_calls = getattr(response_msg, "tool_calls", None)
            if not tool_calls:
                break

            # Add assistant message with tool_calls
            messages.append({
                "role": "assistant",
                "content": getattr(response_msg, "content", "") or "",
                "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls],
            })

            # Execute each tool and add result
            for tc in tool_calls:
                args = _json.loads(tc.function.arguments or "{}")
                result = _execute_tool(tc.function.name, args)
                tool_results_summary.append(f"{tc.function.name}: {result}")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        # Final streaming response — send all messages including tool results
        for chunk in stream_groq_messages(messages):
            asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
    except Exception as e:
        asyncio.run_coroutine_threadsafe(queue.put(f"⚠️ Groq error: {e}"), loop)
    finally:
        asyncio.run_coroutine_threadsafe(queue.put(None), loop)


def _run_agent(client, contents, tools, queue, loop):
    try:
        from google.genai import types
        config = types.GenerateContentConfig(
            tools=tools,
            system_instruction=SYSTEM_PROMPT,
        )

        for model in MODELS:
            try:
                working_contents = list(contents)
                MAX_ROUNDS = 5
                for _ in range(MAX_ROUNDS):
                    response = client.models.generate_content(model=model, contents=working_contents, config=config)
                    model_content = response.candidates[0].content
                    fc_parts = [p for p in model_content.parts if hasattr(p, "function_call") and p.function_call and p.function_call.name]
                    if not fc_parts:
                        break
                    fn_response_parts = []
                    for part in fc_parts:
                        fc = part.function_call
                        result = _execute_tool(fc.name, dict(fc.args))
                        fn_response_parts.append(
                            types.Part.from_function_response(name=fc.name, response={"output": result})
                        )
                    working_contents.append(model_content)
                    working_contents.append(types.Content(role="user", parts=fn_response_parts))

                for chunk in client.models.generate_content_stream(model=model, contents=working_contents, config=config):
                    if chunk.text:
                        asyncio.run_coroutine_threadsafe(queue.put(chunk.text), loop)
                return  # success
            except Exception as e:
                if _is_rate_limit(e) and model != MODELS[-1]:
                    continue
                if _is_rate_limit(e):
                    # Fall back to Groq
                    _run_groq_agent(contents, queue, loop)
                else:
                    asyncio.run_coroutine_threadsafe(queue.put("⚠️ Something went wrong. Please try again."), loop)
                return
    except Exception as e:
        asyncio.run_coroutine_threadsafe(queue.put("⚠️ Something went wrong. Please try again."), loop)
    finally:
        asyncio.run_coroutine_threadsafe(queue.put(None), loop)


@router.post("")
async def chat(req: ChatRequest):
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        async def _err():
            yield "data: " + json.dumps({"text": "⚠️ google-genai not installed."}) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        async def _err():
            yield "data: " + json.dumps({"text": "⚠️ GEMINI_API_KEY not set."}) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    client = genai.Client(api_key=api_key)
    tools = _build_tools()

    # Build conversation history
    contents = []
    for h in req.history:
        role = "user" if h.get("role") == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=h.get("content", ""))]))
    contents.append(types.Content(role="user", parts=[types.Part(text=req.message)]))

    async def generate():
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        thread = threading.Thread(target=_run_agent, args=(client, contents, tools, queue, loop), daemon=True)
        thread.start()
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield "data: " + json.dumps({"text": chunk}) + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
