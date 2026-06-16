# -*- coding: utf-8 -*-
from typing import Optional

from pydantic import BaseModel


class ViolationTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_penalty_points: Optional[int] = None


class ViolationTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_penalty_points: Optional[int] = None


class ViolationTypeDirectoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    default_penalty_points: Optional[int] = None


class ActivityTypeCreate(BaseModel):
    activity_name: str
    description: Optional[str] = None


class ActivityTypeUpdate(BaseModel):
    activity_name: Optional[str] = None
    description: Optional[str] = None


class ActivityTypeDirectoryResponse(BaseModel):
    id: int
    activity_name: str
    description: Optional[str] = None
