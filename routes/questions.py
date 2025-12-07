from fastapi import APIRouter
from services.questions import load_questions

router = APIRouter(prefix="/questions", tags=["Questions"])

@router.get("/")
def fetch_questions():
    return load_questions()
