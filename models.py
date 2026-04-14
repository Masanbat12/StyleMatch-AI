from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    skin_tone: str = Field(..., min_length=1)
    undertone: str = Field(..., min_length=1)
    style: str = Field(..., min_length=1)
    occasion: str = Field(..., min_length=1)


class Outfit(BaseModel):
    shirt_color: str = Field(..., min_length=1)
    pants_color: str = Field(..., min_length=1)
    shoes_color: str = Field(..., min_length=1)
    score: int = 0
