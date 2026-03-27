import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

_PATH = Path(__file__).parent.parent.parent / "config" / "alerts.json"


def _load() -> dict:
    if _PATH.exists():
        return json.loads(_PATH.read_text())
    return {"email": "", "alerts": []}


def _save(data: dict):
    _PATH.write_text(json.dumps(data, indent=2))


class AlertConfig(BaseModel):
    email: str


class AlertThreshold(BaseModel):
    above: float = None
    below: float = None


@router.get("")
def get_alerts():
    return _load()


@router.put("/config")
def set_email(body: AlertConfig):
    data = _load()
    data["email"] = body.email
    _save(data)
    return data


@router.post("/{symbol}")
def set_alert(symbol: str, body: AlertThreshold):
    sym = symbol.upper().strip()
    data = _load()
    # Remove existing alert for this symbol
    data["alerts"] = [a for a in data["alerts"] if a["symbol"] != sym]
    if body.above is not None or body.below is not None:
        data["alerts"].append({
            "symbol": sym,
            "above": body.above,
            "below": body.below,
            "triggered_above": False,
            "triggered_below": False,
        })
    _save(data)
    return data


@router.delete("/{symbol}")
def remove_alert(symbol: str):
    sym = symbol.upper().strip()
    data = _load()
    data["alerts"] = [a for a in data["alerts"] if a["symbol"] != sym]
    _save(data)
    return data
