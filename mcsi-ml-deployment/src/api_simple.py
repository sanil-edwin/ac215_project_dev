from fastapi import FastAPI
import joblib
from pathlib import Path

app = FastAPI()

rf_model = None

@app.on_event("startup")
async def load():
    global rf_model
    rf_model = joblib.load('./models/rf_model.pkl')

@app.get("/health")
async def health():
    return {"status": "healthy", "models_loaded": rf_model is not None}

@app.get("/model/info")
async def info():
    return {"model": "Random Forest", "mae": "14.58 bu/acre"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
