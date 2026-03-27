import json
from fastapi import APIRouter
from data.trending import get_trending_stocks
from ai.gemini_client import generate_trending_commentary
from ui.charts import plot_trending_treemap

router = APIRouter(prefix="/api/trending", tags=["trending"])


@router.get("")
def trending_stocks(top_n: int = 15):
    df = get_trending_stocks(top_n=top_n)
    if df.empty:
        return []
    return df.to_dict(orient="records")


@router.get("/chart-json")
def trending_chart_json(top_n: int = 15):
    df = get_trending_stocks(top_n=top_n)
    if df.empty:
        return {}
    fig = plot_trending_treemap(df)
    return json.loads(fig.to_json())


@router.get("/commentary")
def trending_commentary():
    df = get_trending_stocks(top_n=5)
    text = generate_trending_commentary(df)
    return {"text": text}
