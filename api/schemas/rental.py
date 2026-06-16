# -*- coding: utf-8 -*-
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class RentalListingCreate(BaseModel):
    title: str
    description: str
    daily_price: float
    category_id: Optional[int] = None
    deposit_amount: Optional[float] = 0
    dormitory_id: Optional[int] = None
    pickup_location: Optional[str] = None
    minimum_rental_period_text: Optional[str] = None
    contact_name: str
    contact_value: str
    contact_note: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)


class RentalListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    daily_price: Optional[float] = None
    category_id: Optional[int] = None
    deposit_amount: Optional[float] = None
    dormitory_id: Optional[int] = None
    pickup_location: Optional[str] = None
    minimum_rental_period_text: Optional[str] = None
    contact_name: Optional[str] = None
    contact_value: Optional[str] = None
    contact_note: Optional[str] = None
    image_urls: Optional[list[str]] = None
    listing_status: Optional[str] = None
    status: Optional[str] = None


class RentalListingResponse(BaseModel):
    id: int
    is_rental: bool = True
    marketplace_type: str
    title: str
    description: str
    daily_price: float
    deposit_amount: float
    owner_id: int
    owner_name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    dormitory_id: Optional[int] = None
    dormitory_name: Optional[str] = None
    pickup_location: Optional[str] = None
    minimum_rental_period_text: Optional[str] = None
    contact_name: Optional[str] = None
    contact_value: Optional[str] = None
    contact_note: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)
    status: str
    listing_status: str
    availability_status: str
    is_owner: bool = False
    created_at: datetime
    updated_at: datetime


class RentalListingListResponse(BaseModel):
    items: list[RentalListingResponse]
    total: int
    limit: int
    offset: int


class RentalCategoryOption(BaseModel):
    id: int
    name: str


class RentalDormitoryOption(BaseModel):
    id: int
    name: str


class RentalFilterOptionsResponse(BaseModel):
    categories: list[RentalCategoryOption]
    dormitories: list[RentalDormitoryOption]


class RentalBookingCreate(BaseModel):
    listing_id: int
    start_date: date
    end_date: date
    comment: Optional[str] = None


class RentalBookingUpdate(BaseModel):
    status: Optional[str] = None
    deposit_amount: Optional[float] = None
    fine_amount: Optional[float] = None
    comment: Optional[str] = None
    approved_by_id: Optional[int] = None


class RentalBookingResponse(BaseModel):
    id: int
    listing_id: int
    listing_title: str
    renter_id: int
    renter_name: str
    approved_by_id: Optional[int] = None
    approved_by_name: Optional[str] = None
    start_date: date
    end_date: date
    status: str
    deposit_amount: float
    fine_amount: float
    total_price: float
    comment: Optional[str] = None
    created_at: datetime


class RentalBookingListResponse(BaseModel):
    items: list[RentalBookingResponse]
    total: int
