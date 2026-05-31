from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class UserRecord(BaseModel):
    """
    Pydantic schema for validating raw user records from the source API.
    Any record that fails validation is logged and skipped — not silently corrupted.
    """

    id: int
    name: str
    username: str
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None

    @field_validator("name", "username")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field must not be blank or whitespace only.")
        return v

    @field_validator("email")
    @classmethod
    def basic_email_check(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError(f"Invalid email format: {v!r}")
        return v
