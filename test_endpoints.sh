#!/bin/bash
set -e

API_URL="https://signal-clone-backend-xja6.onrender.com/api/v1/auth"
PHONE="+19998887777"
EMAIL="test@example.com"

echo "1. Testing /otp/send"
SEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"phone\": \"$PHONE\", \"email\": \"$EMAIL\"}" "$API_URL/otp/send")
echo "HTTP $SEND_RESPONSE"

echo "2. Testing /otp/verify"
VERIFY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"phone\": \"$PHONE\", \"otp\": \"000000\"}" "$API_URL/otp/verify")
echo "HTTP $VERIFY_RESPONSE"

echo "3. Testing /register"
REGISTER_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"registration_token\": \"invalid-token\", \"username\": \"testuser\", \"display_name\": \"Test\", \"password\": \"Pass123!\"}" "$API_URL/register")
echo "HTTP $REGISTER_RESPONSE"

echo "4. Testing /login"
LOGIN_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "{\"username\": \"testuser\", \"password\": \"Wrong123!\"}" "$API_URL/login")
echo "HTTP $LOGIN_RESPONSE"

