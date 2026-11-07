
import re
from pathlib import Path
from app.brokers.zerodha import zerodha_service
from fastapi import APIRouter, HTTPException, Query

from app.data.loader import load_ohlcv_csv
from app.strategies.trend_following import generate_trend_signal

router = APIRouter(tags=["Trading"])
@router.get("/auth/login")
def zerodha_login():
    try:
        return {
            "login_url": zerodha_service.get_login_url()
        }
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Zerodha API key is not configured",
        )


@router.get("/auth/callback")
def zerodha_callback(request_token: str):
    try:
        result = zerodha_service.complete_login(request_token)
        return {
            "message": "Zerodha authentication successful",
            **result,
        }
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Zerodha API credentials are not configured",
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Zerodha authentication failed. Please log in again.",
        )


@router.get("/auth/status")
def zerodha_auth_status():
    return {
        "authenticated": zerodha_service.is_authenticated
    }

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "raw"

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9&_-]{0,29}$")


@router.get("/strategies")
def get_strategies():
    return {
        "strategies": [
            "trend_following"
        ]
    }


def validate_symbol(symbol: str) -> str:
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise HTTPException(
            status_code=400,
            detail="Invalid stock symbol",
        )

    return symbol.upper()


def load_symbol_data(symbol: str):
    validated_symbol = validate_symbol(symbol)
    file_path = DATA_DIR / f"{validated_symbol}.csv"

    try:
        return validated_symbol, load_ohlcv_csv(file_path)

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Historical data not found for {validated_symbol}",
        )

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/market-data/{symbol}")
def get_market_data(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=1000),
):
    validated_symbol, df = load_symbol_data(symbol)

    records = df.tail(limit).copy()
    records["date"] = records["date"].dt.strftime("%Y-%m-%d")

    return {
        "symbol": validated_symbol,
        "count": len(records),
        "data": records.to_dict(orient="records"),
    }


@router.get("/signals/trend/{symbol}")
def get_trend_signal(symbol: str):
    validated_symbol, df = load_symbol_data(symbol)

    return {
        "symbol": validated_symbol,
        **generate_trend_signal(df),
    }

@router.get("/auth/profile")
def zerodha_profile():
    try:
        profile = zerodha_service.get_profile()

        return {
            "authenticated": True,
            "user_id": profile.get("user_id"),
            "user_name": profile.get("user_name"),
            "broker": profile.get("broker"),
            "exchanges": profile.get("exchanges", []),
            "products": profile.get("products", []),
        }

    except RuntimeError:
        raise HTTPException(
            status_code=401,
            detail="Zerodha authentication required",
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve Zerodha profile",
        )