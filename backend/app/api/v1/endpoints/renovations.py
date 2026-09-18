"""公厕改造项目接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.database import get_db
from app.schemas.common import Page
from app.schemas.renovation import (
    RenovationCreate,
    RenovationMilestoneCreate,
    RenovationOut,
    RenovationStatusUpdate,
    RenovationUpdate,
)
from app.services import renovation_service

router = APIRouter(prefix="/renovations", tags=["改造项目"])


class TransitionOption(BaseModel):
    status: str
    action: str


@router.get("", response_model=Page[RenovationOut], summary="改造项目列表")
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    status: Annotated[str | None, Query(description="项目状态")] = None,
    keyword: Annotated[str | None, Query(description="名称/编号/施工单位模糊搜索")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "created_at",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[RenovationOut]:
    rows, total = renovation_service.list_projects(
        db,
        restroom_id=restroom_id,
        district=district,
        status=status,
        keyword=keyword,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[RenovationOut](
        items=[renovation_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=RenovationOut, status_code=201, summary="立项登记")
def create_project(
    payload: RenovationCreate, db: Annotated[Session, Depends(get_db)]
) -> RenovationOut:
    return renovation_service.to_out(renovation_service.create_project(db, payload))


@router.get("/{project_id}", response_model=RenovationOut, summary="项目详情与档案")
def get_project(project_id: int, db: Annotated[Session, Depends(get_db)]) -> RenovationOut:
    return renovation_service.to_out(renovation_service.get_project(db, project_id))


@router.patch("/{project_id}", response_model=RenovationOut, summary="更新项目信息")
def update_project(
    project_id: int, payload: RenovationUpdate, db: Annotated[Session, Depends(get_db)]
) -> RenovationOut:
    return renovation_service.to_out(renovation_service.update_project(db, project_id, payload))


@router.get(
    "/{project_id}/transitions",
    response_model=list[TransitionOption],
    summary="可执行的项目动作",
)
def list_transitions(
    project_id: int, db: Annotated[Session, Depends(get_db)]
) -> list[TransitionOption]:
    project = renovation_service.get_project(db, project_id)
    return [
        TransitionOption(**option) for option in renovation_service.allowed_transitions(project)
    ]


@router.post("/{project_id}/transitions", response_model=RenovationOut, summary="推进项目状态")
def change_status(
    project_id: int, payload: RenovationStatusUpdate, db: Annotated[Session, Depends(get_db)]
) -> RenovationOut:
    return renovation_service.to_out(renovation_service.change_status(db, project_id, payload))


@router.post("/{project_id}/milestones", response_model=RenovationOut, summary="记录节点进度")
def add_milestone(
    project_id: int, payload: RenovationMilestoneCreate, db: Annotated[Session, Depends(get_db)]
) -> RenovationOut:
    project = renovation_service.add_milestone(db, project_id, payload)
    return renovation_service.to_out(project)
