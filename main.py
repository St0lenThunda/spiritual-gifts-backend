from fastapi import FastAPI
from routes.questions import router as questions_router

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Spiritual Gifts API Running"}

app.include_router(questions_router)
