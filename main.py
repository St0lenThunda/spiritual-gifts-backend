from fastapi import FastAPI
from routes.api import router as api_router

app = FastAPI()

@app.get("/")   
def root():
    return {"message": "Spiritual Gifts API Running"}

app.include_router(api_router)
