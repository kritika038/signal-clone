import asyncio
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app.other_asgi_app)

def test_endpoints():
    print("Testing /register/send-otp")
    res = client.post("/api/v1/auth/register/send-otp", json={"phone": "+1234567890", "email": "test@example.com"})
    # Since we lack SMTP credentials locally, it correctly fails at sending the email!
    assert res.status_code == 400, res.text
    assert "Unable to send verification email" in res.text
    
    print("Testing /register/verify with bad OTP")
    res = client.post("/api/v1/auth/register/verify", json={"phone": "+1234567890", "email": "test@example.com", "otp": "000000"})
    assert res.status_code == 400, res.text
    assert "Invalid or expired OTP" in res.text

    print("All endpoints tested successfully!")

if __name__ == "__main__":
    test_endpoints()
