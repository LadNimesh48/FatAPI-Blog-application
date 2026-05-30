from fastapi import FastAPI
from fastapi.testclient import TestClient

demo_app = FastAPI()

@demo_app.get("/")
def home():
    return {"msg": "Home Route"}

client = TestClient(demo_app)

def test_homepage():
    response = client.get("/")
    assert response.status_code == 200
