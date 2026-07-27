from fastapi.testclient import TestClient
from app.main import app
import uuid
import random

client = TestClient(app)
phone = f"+1555{random.randint(1000000, 9999999)}"
username = f"user_{uuid.uuid4().hex[:7]}"

# 1. Send OTP
res1 = client.post("/api/v1/auth/register/send-otp", json={"phone": phone})
print("Send OTP:", res1.json())

# 2. Verify OTP
res2 = client.post("/api/v1/auth/register/verify", json={"phone": phone, "otp": "123456"})
print("Verify OTP:", res2.json())
token = res2.json()["data"]["registration_token"]

# 3. Register
try:
    res3 = client.post("/api/v1/auth/register", json={
        "registration_token": token,
        "username": username,
        "display_name": "Test User",
        "phone": phone
    })
    print("Register Status:", res3.status_code)
    try:
        print("Register JSON:", res3.json())
    except:
        print("Register Text:", res3.text)
except Exception as e:
    import traceback
    traceback.print_exc()
