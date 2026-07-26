#!/bin/bash
set -e

API_URL="https://signal-clone-backend-xja6.onrender.com/api/v1/auth"
PHONE="+1$(date +%s)"
EMAIL="test$(date +%s)@example.com"
USERNAME="user$(date +%s)"
PASSWORD="Password123!"

echo "1. Testing /otp/send"
SEND_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"phone\": \"$PHONE\", \"email\": \"$EMAIL\"}" "$API_URL/otp/send")
echo "$SEND_RESPONSE"
OTP=$(echo "$SEND_RESPONSE" | jq -r '.data.otp_mock')

if [ -z "$OTP" ] || [ "$OTP" = "null" ]; then
    echo "Failed to extract OTP!"
    exit 1
fi
echo "Received OTP: $OTP"

echo "2. Testing /otp/verify"
VERIFY_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"phone\": \"$PHONE\", \"otp\": \"$OTP\"}" "$API_URL/otp/verify")
echo "$VERIFY_RESPONSE"
REG_TOKEN=$(echo "$VERIFY_RESPONSE" | jq -r '.data.registration_token')

if [ -z "$REG_TOKEN" ] || [ "$REG_TOKEN" = "null" ]; then
    echo "Failed to extract registration token!"
    exit 1
fi
echo "Received Registration Token: $REG_TOKEN"

echo "3. Testing /register"
REGISTER_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"registration_token\": \"$REG_TOKEN\", \"username\": \"$USERNAME\", \"display_name\": \"Test User\", \"password\": \"$PASSWORD\", \"avatar_url\": \"avatar_1.png\"}" "$API_URL/register")
echo "$REGISTER_RESPONSE"
SUCCESS=$(echo "$REGISTER_RESPONSE" | jq -r '.success')

if [ "$SUCCESS" != "true" ]; then
    echo "Registration failed!"
    exit 1
fi
echo "Registration succeeded."

echo "4. Testing /login"
LOGIN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}" "$API_URL/login")
echo "$LOGIN_RESPONSE"
LOGIN_SUCCESS=$(echo "$LOGIN_RESPONSE" | jq -r '.success')

if [ "$LOGIN_SUCCESS" != "true" ]; then
    echo "Login failed!"
    exit 1
fi
echo "Login succeeded! All checks passed."
