# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ServiceRequestAttachmentCreate(BaseModel):
    file_name: str
    file_url: str


class ServiceRequestAttachmentResponse(BaseModel):
    id: int
    file_name: str
    file_url: str
    uploaded_by_id: Optional[int] = None
    uploaded_by_name: Optional[str] = None
    created_at: datetime


class ServiceRequestCommentCreate(BaseModel):
    comment: str


class ServiceRequestCommentResponse(BaseModel):
    id: int
    author_id: int
    author_name: str
    comment: str
    created_at: datetime


class ServiceRequestCreate(BaseModel):
    title: str
    description: str
    request_type: str
    dormitory_id: Optional[int] = None
    room_id: Optional[int] = None
    student_id: Optional[int] = None
    executor_id: Optional[int] = None
    attachments: list[ServiceRequestAttachmentCreate] = []


class ServiceRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    request_type: Optional[str] = None
    status: Optional[str] = None
    dormitory_id: Optional[int] = None
    room_id: Optional[int] = None
    student_id: Optional[int] = None
    executor_id: Optional[int] = None
    resolution_comment: Optional[str] = None
    attachments: Optional[list[ServiceRequestAttachmentCreate]] = None


class ServiceRequestResponse(BaseModel):
    id: int
    title: str
    description: str
    request_type: str
    status: str
    student_id: int
    student_name: str
    executor_id: Optional[int] = None
    executor_name: Optional[str] = None
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    room_id: Optional[int] = None
    room_number: Optional[int] = None
    resolution_comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    comments: list[ServiceRequestCommentResponse] = []
    attachments: list[ServiceRequestAttachmentResponse] = []


class ServiceRequestListResponse(BaseModel):
    items: list[ServiceRequestResponse]
    total: int
