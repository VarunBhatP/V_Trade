from fastapi import FastAPI

app = FastAPI(
    title="QuantTrader",
    description="Systematic Trading Research Platform",
    version="0.1.0"
)

@app.get("/")
def root():
    return {"message": "QuantTrader API running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/strategies")
def get_strategies():
    return {
        "strategies": [
            "trend_following",
            "momentum",
            "mean_reversion",
            "breakout",
            "volatility_breakout"
        ]
    }