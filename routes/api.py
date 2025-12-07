from fastapi import APIRouter
from services.getJSONData import load_questions, load_gifts

router = APIRouter()

@router.get("/questions")
def fetch_questions():
    return load_questions()

@router.get("/gifts")
def fetch_gifts():
    return load_gifts()

