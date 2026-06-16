# -*- coding: utf-8 -*-
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.db.models import Category, Dormitory, RentalBooking, RentalListing, User
from api.schemas.rental import (
    RentalBookingCreate,
    RentalBookingListResponse,
    RentalBookingResponse,
    RentalBookingUpdate,
    RentalCategoryOption,
    RentalDormitoryOption,
    RentalFilterOptionsResponse,
    RentalListingCreate,
    RentalListingListResponse,
    RentalListingResponse,
    RentalListingUpdate,
)
from api.services.user_helpers import can_moderate_products

router = APIRouter(prefix="/api/v1/rentals")
legacy_router = APIRouter(prefix="/rentals")

ALLOWED_LISTING_STATUSES = {"active", "paused", "archived"}
ALLOWED_REVIEW_STATUSES = {"pending", "approved", "rejected"}
ALLOWED_BOOKING_STATUSES = {
    "pending",
    "approved",
    "active",
    "completed",
    "cancelled",
    "rejected",
}
RENTAL_CATEGORY_NAMES = (
    "Техника",
    "Инструменты",
    "Учеба",
    "Спорт",
    "Мебель",
    "Другое",
)


def _has_moderation_access(user: User | None) -> bool:
    return can_moderate_products(user)


def _normalize_image_urls(raw_value) -> list[str]:
    if isinstance(raw_value, list):
        return [str(item) for item in raw_value if str(item).strip()]
    if isinstance(raw_value, dict):
        return [str(item) for item in raw_value.values() if str(item).strip()]
    return []


def _validate_listing_status(status: str) -> None:
    if status not in ALLOWED_LISTING_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid listing_status. Allowed values: {sorted(ALLOWED_LISTING_STATUSES)}",
        )


def _validate_review_status(status: str) -> None:
    if status not in ALLOWED_REVIEW_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed values: {sorted(ALLOWED_REVIEW_STATUSES)}",
        )


def _validate_booking_status(status: str) -> None:
    if status not in ALLOWED_BOOKING_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid booking status. Allowed values: {sorted(ALLOWED_BOOKING_STATUSES)}",
        )


def _build_listing_response(
    listing: RentalListing,
    *,
    current_user_id: int | None = None,
    owner: User | None = None,
    category: Category | None = None,
    dormitory: Dormitory | None = None,
) -> RentalListingResponse:
    owner = owner or listing.owner
    category = category or listing.category
    dormitory = dormitory or listing.dormitory

    return RentalListingResponse(
        id=listing.id,
        is_rental=True,
        marketplace_type="rental",
        title=listing.title,
        description=listing.description,
        daily_price=float(listing.daily_price),
        deposit_amount=float(listing.deposit_amount),
        owner_id=listing.owner_id,
        owner_name=owner.full_name if owner else "Unknown",
        category_id=listing.category_id,
        category_name=category.name if category else None,
        dormitory_id=listing.dormitory_id,
        dormitory_name=dormitory.name if dormitory else None,
        pickup_location=listing.pickup_location,
        minimum_rental_period_text=listing.minimum_rental_period_text,
        contact_name=listing.contact_name,
        contact_value=listing.contact_value,
        contact_note=listing.contact_note,
        image_urls=_normalize_image_urls(listing.image_urls),
        status=listing.status,
        listing_status=listing.listing_status,
        availability_status=listing.availability_status,
        is_owner=current_user_id == listing.owner_id,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


def _build_booking_response(booking: RentalBooking) -> RentalBookingResponse:
    return RentalBookingResponse(
        id=booking.id,
        listing_id=booking.listing_id,
        listing_title=booking.listing.title if booking.listing else "Unknown",
        renter_id=booking.renter_id,
        renter_name=booking.renter.full_name if booking.renter else "Unknown",
        approved_by_id=booking.approved_by_id,
        approved_by_name=booking.approved_by.full_name if booking.approved_by else None,
        start_date=booking.start_date,
        end_date=booking.end_date,
        status=booking.status,
        deposit_amount=float(booking.deposit_amount),
        fine_amount=float(booking.fine_amount),
        total_price=float(booking.total_price),
        comment=booking.comment,
        created_at=booking.created_at,
    )


def _get_listing_or_404(db: Session, listing_id: int) -> RentalListing:
    listing = (
        db.query(RentalListing)
        .options(
            joinedload(RentalListing.owner),
            joinedload(RentalListing.dormitory),
            joinedload(RentalListing.category),
        )
        .filter(RentalListing.id == listing_id)
        .first()
    )
    if not listing:
        raise HTTPException(status_code=404, detail="Rental listing not found")
    return listing


def _get_booking_or_404(db: Session, booking_id: int) -> RentalBooking:
    booking = (
        db.query(RentalBooking)
        .options(
            joinedload(RentalBooking.listing).joinedload(RentalListing.owner),
            joinedload(RentalBooking.renter),
            joinedload(RentalBooking.approved_by),
        )
        .filter(RentalBooking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Rental booking not found")
    return booking


def _refresh_listing_availability(db: Session, listing: RentalListing) -> bool:
    occupied_booking = (
        db.query(RentalBooking)
        .filter(
            RentalBooking.listing_id == listing.id,
            RentalBooking.status.in_(["approved", "active"]),
            RentalBooking.end_date >= date.today(),
        )
        .first()
    )
    new_status = "occupied" if occupied_booking else "free"
    if listing.availability_status == new_status:
        return False

    listing.availability_status = new_status
    listing.updated_at = datetime.utcnow()
    return True


def _validate_dates(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be earlier than start_date")


def _check_booking_overlap(
    db: Session,
    listing_id: int,
    start_date: date,
    end_date: date,
    excluded_booking_id: int | None = None,
) -> None:
    query = db.query(RentalBooking).filter(
        RentalBooking.listing_id == listing_id,
        RentalBooking.status.in_(["approved", "active"]),
        RentalBooking.start_date <= end_date,
        RentalBooking.end_date >= start_date,
    )
    if excluded_booking_id is not None:
        query = query.filter(RentalBooking.id != excluded_booking_id)

    if query.first():
        raise HTTPException(status_code=400, detail="Selected dates overlap an existing booking")


def _resolve_dormitory(db: Session, dormitory_id: int | None) -> Dormitory | None:
    if dormitory_id is None:
        return None

    dormitory = db.query(Dormitory).filter(Dormitory.id == dormitory_id).first()
    if dormitory is None:
        raise HTTPException(status_code=404, detail="Dormitory not found")
    return dormitory


def _resolve_category(db: Session, category_id: int | None) -> Category | None:
    if category_id is None:
        return None

    category = db.query(Category).filter(Category.id == category_id).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


def _apply_listing_visibility(query, current_user: User):
    if _has_moderation_access(current_user):
        return query

    return query.filter(
        or_(
            RentalListing.owner_id == current_user.id,
            and_(
                RentalListing.status == "approved",
                RentalListing.listing_status == "active",
            ),
        )
    )


@router.get("/filter-options", response_model=RentalFilterOptionsResponse)
@legacy_router.get("/filter-options", response_model=RentalFilterOptionsResponse)
def get_rental_filter_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    categories = (
        db.query(Category)
        .filter(
            Category.entity_type == "product",
            Category.name.in_(RENTAL_CATEGORY_NAMES),
        )
        .all()
    )
    category_order = {name: index for index, name in enumerate(RENTAL_CATEGORY_NAMES)}
    categories = sorted(
        categories,
        key=lambda item: (category_order.get(item.name, 999), item.id),
    )

    dormitories = db.query(Dormitory).order_by(Dormitory.id.asc()).all()

    return RentalFilterOptionsResponse(
        categories=[
            RentalCategoryOption(id=item.id, name=item.name) for item in categories
        ],
        dormitories=[
            RentalDormitoryOption(id=item.id, name=item.name)
            for item in dormitories
        ],
    )


@router.get("/listings", response_model=RentalListingListResponse)
@legacy_router.get("/listings", response_model=RentalListingListResponse)
def get_rental_listings(
    is_rental: bool = True,
    category_id: int | None = None,
    dormitory_id: int | None = None,
    owner_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rental_price: float | None = None,
    max_rental_price: float | None = None,
    search: str | None = None,
    availability_status: str | None = None,
    listing_status: str | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not is_rental:
        return RentalListingListResponse(items=[], total=0, limit=limit, offset=offset)

    query = db.query(RentalListing)

    if category_id is not None:
        query = query.filter(RentalListing.category_id == category_id)
    if dormitory_id is not None:
        query = query.filter(RentalListing.dormitory_id == dormitory_id)
    if owner_id is not None:
        query = query.filter(RentalListing.owner_id == owner_id)
    if listing_status is not None:
        _validate_listing_status(listing_status)
        query = query.filter(RentalListing.listing_status == listing_status)
    if status is not None:
        _validate_review_status(status)
        query = query.filter(RentalListing.status == status)
    if availability_status is not None:
        if availability_status not in {"free", "occupied"}:
            raise HTTPException(
                status_code=400,
                detail="availability_status must be either free or occupied",
            )
        query = query.filter(RentalListing.availability_status == availability_status)

    normalized_search = (search or "").strip()
    if normalized_search:
        query = query.filter(RentalListing.title.ilike(f"%{normalized_search}%"))

    min_candidates = [value for value in [min_price, min_rental_price] if value is not None]
    max_candidates = [value for value in [max_price, max_rental_price] if value is not None]
    effective_min = max(min_candidates) if min_candidates else None
    effective_max = min(max_candidates) if max_candidates else None

    if effective_min is not None:
        query = query.filter(RentalListing.daily_price >= effective_min)
    if effective_max is not None:
        query = query.filter(RentalListing.daily_price <= effective_max)
    if (
        effective_min is not None and
        effective_max is not None and
        effective_max < effective_min
    ):
        raise HTTPException(status_code=400, detail="max price must be greater than or equal to min price")

    query = _apply_listing_visibility(query, current_user)

    total = query.count()
    if total == 0:
        return RentalListingListResponse(items=[], total=0, limit=limit, offset=offset)

    listings = (
        query.order_by(RentalListing.created_at.desc(), RentalListing.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    did_change = False
    for listing in listings:
        did_change = _refresh_listing_availability(db, listing) or did_change
    if did_change:
        db.commit()

    owner_ids = sorted({item.owner_id for item in listings if item.owner_id is not None})
    category_ids = sorted({item.category_id for item in listings if item.category_id is not None})
    dormitory_ids = sorted({item.dormitory_id for item in listings if item.dormitory_id is not None})

    owners_by_id = {
        item.id: item
        for item in db.query(User).filter(User.id.in_(owner_ids)).all()
    } if owner_ids else {}
    categories_by_id = {
        item.id: item
        for item in db.query(Category).filter(Category.id.in_(category_ids)).all()
    } if category_ids else {}
    dormitories_by_id = {
        item.id: item
        for item in db.query(Dormitory).filter(Dormitory.id.in_(dormitory_ids)).all()
    } if dormitory_ids else {}

    return RentalListingListResponse(
        items=[
            _build_listing_response(
                item,
                current_user_id=current_user.id,
                owner=owners_by_id.get(item.owner_id),
                category=categories_by_id.get(item.category_id),
                dormitory=dormitories_by_id.get(item.dormitory_id),
            )
            for item in listings
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/listings/{listing_id}", response_model=RentalListingResponse)
@legacy_router.get("/listings/{listing_id}", response_model=RentalListingResponse)
def get_rental_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(db, listing_id)
    changed = _refresh_listing_availability(db, listing)
    if changed:
        db.commit()
        db.refresh(listing)

    can_view = (
        _has_moderation_access(current_user) or
        listing.owner_id == current_user.id or
        (
            listing.status == "approved" and
            listing.listing_status == "active"
        )
    )
    if not can_view:
        raise HTTPException(status_code=403, detail="Not enough permissions to view this listing")

    return _build_listing_response(listing, current_user_id=current_user.id)


@router.post("/listings", response_model=RentalListingResponse)
@legacy_router.post("/listings", response_model=RentalListingResponse)
def create_rental_listing(
    listing_data: RentalListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = _resolve_category(db, listing_data.category_id)
    dormitory = _resolve_dormitory(db, listing_data.dormitory_id)

    if not listing_data.contact_name.strip():
        raise HTTPException(status_code=400, detail="contact_name is required")
    if not listing_data.contact_value.strip():
        raise HTTPException(status_code=400, detail="contact_value is required")

    listing = RentalListing(
        title=listing_data.title.strip(),
        description=listing_data.description.strip(),
        daily_price=listing_data.daily_price,
        deposit_amount=listing_data.deposit_amount or 0,
        owner_id=current_user.id,
        category_id=category.id if category else None,
        dormitory_id=dormitory.id if dormitory else current_user.dormitory_id,
        image_urls=listing_data.image_urls,
        status="approved" if _has_moderation_access(current_user) else "pending",
        listing_status="active",
        availability_status="free",
        pickup_location=(listing_data.pickup_location or "").strip() or None,
        minimum_rental_period_text=(listing_data.minimum_rental_period_text or "").strip() or None,
        contact_name=listing_data.contact_name.strip(),
        contact_value=listing_data.contact_value.strip(),
        contact_note=(listing_data.contact_note or "").strip() or None,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    return _build_listing_response(
        _get_listing_or_404(db, listing.id),
        current_user_id=current_user.id,
    )


@router.put("/listings/{listing_id}", response_model=RentalListingResponse)
@legacy_router.put("/listings/{listing_id}", response_model=RentalListingResponse)
def update_rental_listing(
    listing_id: int,
    listing_data: RentalListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(db, listing_id)
    can_moderate = _has_moderation_access(current_user)

    if not can_moderate and listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to update this listing")

    content_changed = False

    if listing_data.listing_status is not None:
        _validate_listing_status(listing_data.listing_status)
        listing.listing_status = listing_data.listing_status

    if listing_data.status is not None:
        if not can_moderate:
            raise HTTPException(status_code=403, detail="Only moderators can change moderation status")
        _validate_review_status(listing_data.status)
        listing.status = listing_data.status

    if listing_data.title is not None:
        listing.title = listing_data.title.strip()
        content_changed = True
    if listing_data.description is not None:
        listing.description = listing_data.description.strip()
        content_changed = True
    if listing_data.daily_price is not None:
        listing.daily_price = listing_data.daily_price
        content_changed = True
    if listing_data.deposit_amount is not None:
        listing.deposit_amount = listing_data.deposit_amount
        content_changed = True
    if listing_data.image_urls is not None:
        listing.image_urls = listing_data.image_urls
        content_changed = True
    if listing_data.pickup_location is not None:
        listing.pickup_location = listing_data.pickup_location.strip() or None
        content_changed = True
    if listing_data.minimum_rental_period_text is not None:
        listing.minimum_rental_period_text = (
            listing_data.minimum_rental_period_text.strip() or None
        )
        content_changed = True
    if listing_data.contact_name is not None:
        listing.contact_name = listing_data.contact_name.strip() or None
        content_changed = True
    if listing_data.contact_value is not None:
        listing.contact_value = listing_data.contact_value.strip() or None
        content_changed = True
    if listing_data.contact_note is not None:
        listing.contact_note = listing_data.contact_note.strip() or None
        content_changed = True
    if listing_data.category_id is not None:
        category = _resolve_category(db, listing_data.category_id)
        listing.category_id = category.id if category else None
        content_changed = True
    if listing_data.dormitory_id is not None:
        dormitory = _resolve_dormitory(db, listing_data.dormitory_id)
        listing.dormitory_id = dormitory.id if dormitory else None
        content_changed = True

    if content_changed and not can_moderate:
        listing.status = "pending"

    _refresh_listing_availability(db, listing)
    listing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(listing)

    return _build_listing_response(
        _get_listing_or_404(db, listing.id),
        current_user_id=current_user.id,
    )


@router.delete("/listings/{listing_id}", response_model=dict)
@legacy_router.delete("/listings/{listing_id}", response_model=dict)
def delete_rental_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(db, listing_id)
    if not _has_moderation_access(current_user) and listing.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to delete this listing")

    active_booking = (
        db.query(RentalBooking)
        .filter(
            RentalBooking.listing_id == listing.id,
            RentalBooking.status.in_(["approved", "active"]),
        )
        .first()
    )
    if active_booking:
        raise HTTPException(status_code=400, detail="Cannot delete listing with active booking")

    db.delete(listing)
    db.commit()
    return {"message": "Rental listing deleted", "listing_id": listing_id}


@router.get("/bookings", response_model=RentalBookingListResponse)
@legacy_router.get("/bookings", response_model=RentalBookingListResponse)
def get_rental_bookings(
    listing_id: int | None = None,
    renter_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(RentalBooking).options(
        joinedload(RentalBooking.listing).joinedload(RentalListing.owner),
        joinedload(RentalBooking.renter),
        joinedload(RentalBooking.approved_by),
    )

    if listing_id is not None:
        query = query.filter(RentalBooking.listing_id == listing_id)
    if renter_id is not None:
        query = query.filter(RentalBooking.renter_id == renter_id)
    if status is not None:
        _validate_booking_status(status)
        query = query.filter(RentalBooking.status == status)

    if not _has_moderation_access(current_user):
        query = query.join(RentalBooking.listing).filter(
            or_(
                RentalBooking.renter_id == current_user.id,
                RentalListing.owner_id == current_user.id,
            )
        )

    items = query.order_by(RentalBooking.created_at.desc()).all()
    return RentalBookingListResponse(
        items=[_build_booking_response(item) for item in items],
        total=len(items),
    )


@router.get("/bookings/{booking_id}", response_model=RentalBookingResponse)
@legacy_router.get("/bookings/{booking_id}", response_model=RentalBookingResponse)
def get_rental_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = _get_booking_or_404(db, booking_id)
    if (
        not _has_moderation_access(current_user) and
        booking.renter_id != current_user.id and
        booking.listing.owner_id != current_user.id
    ):
        raise HTTPException(status_code=403, detail="Not enough permissions to view this booking")
    return _build_booking_response(booking)


@router.post("/bookings", response_model=RentalBookingResponse)
@legacy_router.post("/bookings", response_model=RentalBookingResponse)
def create_rental_booking(
    booking_data: RentalBookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = _get_listing_or_404(db, booking_data.listing_id)
    if listing.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot book your own listing")
    if listing.status != "approved" or listing.listing_status != "active":
        raise HTTPException(status_code=400, detail="Only approved active listings can be booked")

    _validate_dates(booking_data.start_date, booking_data.end_date)
    _check_booking_overlap(db, listing.id, booking_data.start_date, booking_data.end_date)

    rental_days = (booking_data.end_date - booking_data.start_date).days + 1
    booking = RentalBooking(
        listing_id=listing.id,
        renter_id=current_user.id,
        start_date=booking_data.start_date,
        end_date=booking_data.end_date,
        status="pending",
        deposit_amount=listing.deposit_amount,
        fine_amount=0,
        total_price=float(listing.daily_price) * rental_days,
        comment=booking_data.comment,
    )
    db.add(booking)
    db.commit()
    return _build_booking_response(_get_booking_or_404(db, booking.id))


@router.put("/bookings/{booking_id}", response_model=RentalBookingResponse)
@legacy_router.put("/bookings/{booking_id}", response_model=RentalBookingResponse)
def update_rental_booking(
    booking_id: int,
    booking_data: RentalBookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = _get_booking_or_404(db, booking_id)
    is_moderator = _has_moderation_access(current_user)
    is_owner = booking.listing.owner_id == current_user.id
    is_renter = booking.renter_id == current_user.id

    if not any([is_moderator, is_owner, is_renter]):
        raise HTTPException(status_code=403, detail="Not enough permissions to update this booking")

    if booking_data.status is not None:
        _validate_booking_status(booking_data.status)

    if is_renter and not any([is_moderator, is_owner]):
        if booking_data.status not in {None, "cancelled"}:
            raise HTTPException(status_code=403, detail="Renter can only cancel their booking")
        if booking_data.deposit_amount is not None or booking_data.fine_amount is not None:
            raise HTTPException(status_code=403, detail="Renter cannot change deposit or fine")

    if booking_data.status in {"approved", "active"}:
        _check_booking_overlap(
            db,
            booking.listing_id,
            booking.start_date,
            booking.end_date,
            excluded_booking_id=booking.id,
        )

    if booking_data.status is not None:
        booking.status = booking_data.status
        if booking_data.status in {"approved", "active", "completed", "rejected"} and any([is_moderator, is_owner]):
            booking.approved_by_id = current_user.id

    if booking_data.deposit_amount is not None and any([is_moderator, is_owner]):
        booking.deposit_amount = booking_data.deposit_amount
    if booking_data.fine_amount is not None and any([is_moderator, is_owner]):
        booking.fine_amount = booking_data.fine_amount
    if booking_data.comment is not None:
        booking.comment = booking_data.comment

    _refresh_listing_availability(db, booking.listing)
    db.commit()
    return _build_booking_response(_get_booking_or_404(db, booking.id))
