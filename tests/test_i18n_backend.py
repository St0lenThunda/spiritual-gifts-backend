import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from sqlalchemy.orm import Session
import json

client = TestClient(app)

def test_get_gifts_i18n(client, db):
    """
    Verify that /api/v1/gifts returns translated content based on Accept-Language header.
    """
    # 1. Test English (Default)
    response = client.get("/api/v1/gifts", headers={"Accept-Language": "en"})
    assert response.status_code == 200
    gifts_en = response.json()
    assert "Administration" in gifts_en
    assert gifts_en["Administration"]["name"] == "Administration"

    # 2. Test Spanish
    response = client.get("/api/v1/gifts", headers={"Accept-Language": "es"})
    assert response.status_code == 200
    gifts_es = response.json()
    assert "Administration" in gifts_es
    assert gifts_es["Administration"]["name"] == "Administración"

    # 3. Test French
    response = client.get("/api/v1/gifts", headers={"Accept-Language": "fr"})
    assert response.status_code == 200
    gifts_fr = response.json()
    assert "Administration" in gifts_fr
    assert gifts_fr["Giving"]["name"] == "Libéralité"

    # 4. Test Russian
    response = client.get("/api/v1/gifts", headers={"Accept-Language": "ru"})
    assert response.status_code == 200
    gifts_ru = response.json()
    assert "Administration" in gifts_ru
    assert gifts_ru["Administration"]["name"] == "Управление"

def test_get_questions_i18n(client, db):
    """
    Verify that /api/v1/questions returns translated content based on Accept-Language header.
    """
    # 1. Test English
    response = client.get("/api/v1/questions", headers={"Accept-Language": "en"})
    assert response.status_code == 200
    data_en = response.json()
    questions_en = data_en["assessment"]["questions"]
    assert len(questions_en) > 0
    # Check first question
    assert "I" in questions_en[0]["text"] or "my" in questions_en[0]["text"].lower()

    # 2. Test Spanish
    response = client.get("/api/v1/questions", headers={"Accept-Language": "es"})
    assert response.status_code == 200
    data_es = response.json()
    questions_es = data_es["assessment"]["questions"]
    assert len(questions_es) > 0
    # Check Spanish content (Assuming questions_es.json starts with "Me gusta")
    assert "gust" in questions_es[0]["text"].lower()

def test_locale_query_param_override(client, db):
    """
    Verify that the 'locale' query parameter overrides the Accept-Language header.
    """
    # Accept-Language is Russian, but locale param is Spanish
    response = client.get("/api/v1/gifts?locale=es", headers={"Accept-Language": "ru"})
    assert response.status_code == 200
    gifts = response.json()
    assert gifts["Administration"]["name"] == "Administración"
