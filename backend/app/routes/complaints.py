import uuid

from fastapi import APIRouter, Depends, Query

from app.deps import get_complaint_service, rate_limit
from app.domain import Category, Priority, Status
from app.repositories.complaints import ComplaintFilter
from app.schemas import ComplaintIn, ComplaintOut, ComplaintPage, StatusIn
from app.services.complaints import ComplaintService

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post("", status_code=201, response_model=ComplaintOut, dependencies=[Depends(rate_limit)])
def create_complaint(
    body: ComplaintIn, svc: ComplaintService = Depends(get_complaint_service)
) -> ComplaintOut:
    return ComplaintOut.model_validate(svc.create(body.text, body.location, body.reporter_contact))


@router.get("", response_model=ComplaintPage)
def list_complaints(
    category: Category | None = None,
    priority: Priority | None = None,
    status: Status | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: ComplaintService = Depends(get_complaint_service),
) -> ComplaintPage:
    flt = ComplaintFilter(
        category=category.value if category else None,
        priority=priority.value if priority else None,
        status=status.value if status else None,
    )
    items, total = svc.search(flt, page, page_size)
    return ComplaintPage(
        items=[ComplaintOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: uuid.UUID, svc: ComplaintService = Depends(get_complaint_service)
) -> ComplaintOut:
    return ComplaintOut.model_validate(svc.get(complaint_id))


@router.patch("/{complaint_id}/status", response_model=ComplaintOut)
def update_status(
    complaint_id: uuid.UUID,
    body: StatusIn,
    svc: ComplaintService = Depends(get_complaint_service),
) -> ComplaintOut:
    return ComplaintOut.model_validate(svc.change_status(complaint_id, body.status))
