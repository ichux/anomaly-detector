from fastapi import FastAPI
from web.api.v1 import additional_endpoints, endpoints

app = FastAPI(title="Anomaly Detection API")


app.include_router(endpoints.router, tags=["Basic Endpoints"])
app.include_router(additional_endpoints.router, tags=["Additional Endpoints"])
