import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class RegisterSendOTP(BaseModel):
    phone: str = Field(..., examples=["+12025550101"])

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        if not pattern.match(v):
            raise ValueError("Phone number must comply with E.164 standard formatting (e.g. +12025550101)")
        return v

class RegisterVerifyOTP(BaseModel):
    phone: str = Field(..., examples=["+12025550101"])
    otp: str = Field(..., min_length=6, max_length=6, examples=["123456"])

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        if not pattern.match(v):
            raise ValueError("Phone number must comply with E.164 standard formatting")
        return v

class UserRegister(BaseModel):
    registration_token: str = Field(...)
    phone: str = Field(..., examples=["+12025550101"])
    username: str = Field(..., min_length=3, max_length=50, examples=["alice"])
    display_name: str = Field(..., min_length=1, max_length=100, examples=["Alice Smith"])
    avatar_url: Optional[str] = Field(default=None, max_length=255)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        if not pattern.match(v):
            raise ValueError("Phone number must comply with E.164 standard formatting (e.g. +12025550101)")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("Username can only contain alphanumeric characters and underscores")
        return v.lower()

class LoginSendOTP(BaseModel):
    login_id: str = Field(..., description="Phone number (E.164)", examples=["+12025550101"])

class LoginVerifyOTP(BaseModel):
    login_id: str = Field(..., description="Phone number (E.164)", examples=["+12025550101"])
    otp: str = Field(..., min_length=6, max_length=6, examples=["123456"])

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=255)
    avatar_url: Optional[str] = Field(default=None, max_length=255)
    theme: Optional[str] = Field(default=None, examples=["dark", "light"])
    language: Optional[str] = Field(default=None, max_length=10)
    privacy_last_seen: Optional[str] = Field(default=None, examples=["EVERYBODY", "CONTACTS", "NOBODY"])
    privacy_profile_photo: Optional[str] = Field(default=None, examples=["EVERYBODY", "CONTACTS"])
    privacy_read_receipts: Optional[bool] = None
    privacy_typing_indicator: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    auto_download_media: Optional[bool] = None
    default_disappearing_timer: Optional[int] = None
    font_size: Optional[str] = None
