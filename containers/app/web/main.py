from fastapi import FastAPI
from web.api.v1 import endpoints

app: FastAPI = FastAPI(title="Anomaly Detection API")

app.include_router(endpoints.router, tags=["Endpoints"])
