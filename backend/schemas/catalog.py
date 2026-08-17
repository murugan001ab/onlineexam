from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TopicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120)
    parent_id: Optional[int] = None
    order_index: Optional[int] = None


class TopicUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=120)
    parent_id: Optional[int] = None
    order_index: Optional[int] = None


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    name: str
    slug: str
    parent_id: Optional[int] = None
    order_index: Optional[int] = None


class TopicTree(TopicOut):
    children: list["TopicTree"] = Field(default_factory=list)
