
import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_request_id_returned_in_headers(client):
    """Test that X-Request-ID header is captured in response."""
    request_id = "test-correlation-id-123"
    response = client.get("/health", headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id

def test_request_id_in_error_response(client, monkeypatch):
    """Test that X-Request-ID is in error response body and headers."""
    request_id = "test-error-id-456"
    
    # Mock an endpoint to raise Exception
    from app.main import router
    
    # Effectively we need to make an endpoint fail. 
    # easiest way is to mock a service it calls or path context.
    # but the middleware wraps the call_next.
    
    # Let's define a new route on the app specifically for this test if possible,
    # or just mock a dependency.
    # Since we can't easily modify the app instance here without affecting other tests if we are not careful,
    # let's rely on mocking a route handler that we know exists or adding one.
    
    # But wait, we can't easily add a route to `app` inside a test function effectively for the client unless 
    # we rebuild the client.
    
    # An easier way is to mock a function called by an existing endpoint.
    # Let's pick /health which is simple.
    
    def mock_health():
         raise Exception("Simulated Failure")
         
    # We need to find where health is defined. It's in main.py directly.
    # So we patch app.main.health (if it was imported) or modify the app routes?
    # Modifying app routes at runtime is tricky.
    
    # Better approach: Middleware catches exceptions.
    # We can mock `call_next`? No, `test_client` calls the app.
    
    # Let's try to mock `app.router` handling? No.
    
    # Let's try patching a dependency or a simple function used by a route.
    # `health` is in `app.main`.
    
    monkeypatch.setattr("app.main.health", mock_health)
    
    # Note: FastApi resolves the function at startup. Monkeypatching the function object 
    # in the module might work if it hasn't been "compiled" into the route yet?
    # No, FastAPI reads the function at `app.get` time.
    
    # So monkeypatching `app.main.health` AFTER app creation (which happens at import) won't update the route handler.
    
    # Alternate strategy: Use a new TestClient with a new App that includes a failing route,
    # BUT we need to test the MIDDLEWARE which is on the main `app`.
    # The middleware is added to `app`.
    
    # We can add a route to `app` dynamically?
    # app.include_router(...) works dynamically?
    
    from fastapi import APIRouter
    test_router = APIRouter()
    
    @test_router.get("/test-error")
    def fail_route():
        raise Exception("Simulated Failure")
        
    app.include_router(test_router)
    
    response = client.get("/test-error", headers={"X-Request-ID": request_id})
    
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == request_id
    data = response.json()
    assert data["request_id"] == request_id
    assert data["detail"] == "An unexpected server error occurred. Our team has been notified."
