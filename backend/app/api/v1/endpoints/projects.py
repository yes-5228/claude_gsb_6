"""公厕改造项目跟踪接口。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import PaginationDep, build_meta
from app.core.database import get_db
from app.schemas.common import MessageOut, Page
from app.schemas.renovation import (
    RenovationNodeAcceptance,
    RenovationNodeCreate,
    RenovationProjectCreate,
    RenovationProjectOut,
    RenovationProjectUpdate,
    RenovationStatusUpdate,
)
from app.services import renovation_service

router = APIRouter(prefix="/projects", tags=["改造项目"])


class TransitionOption(BaseModel):
    status: str
    action: str


@router.get("", response_model=Page[RenovationProjectOut], summary="改造项目列表")
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    pagination: PaginationDep,
    restroom_id: Annotated[int | None, Query(description="按公厕过滤")] = None,
    district: Annotated[str | None, Query(description="按区域过滤")] = None,
    status: Annotated[str | None, Query(description="项目状态")] = None,
    open_only: Annotated[bool, Query(description="仅看进行中的项目")] = False,
    delayed: Annotated[bool | None, Query(description="是否工期超期")] = None,
    keyword: Annotated[str | None, Query(description="事由/编号/施工单位/负责人模糊搜索")] = None,
    date_from: Annotated[date | None, Query(description="立项开始日期")] = None,
    date_to: Annotated[date | None, Query(description="立项结束日期")] = None,
    sort_by: Annotated[str, Query(description="排序字段")] = "setup_time",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
) -> Page[RenovationProjectOut]:
    rows, total = renovation_service.list_projects(
        db,
        restroom_id=restroom_id,
        district=district,
        status=status,
        open_only=open_only,
        delayed=delayed,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        page=pagination.page,
        page_size=pagination.page_size,
        sort_by=sort_by,
        order=order,
    )
    return Page[RenovationProjectOut](
        items=[renovation_service.to_out(row) for row in rows],
        meta=build_meta(total, pagination),
    )


@router.post("", response_model=RenovationProjectOut, status_code=201, summary="改造项目立项登记")
def create_project(
    payload: RenovationProjectCreate, db: Annotated[Session, Depends(get_db)]
) -> RenovationProjectOut:
    return renovation_service.to_out(renovation_service.create_project(db, payload))


@router.get("/{project_id}", response_model=RenovationProjectOut, summary="改造项目详情与档案")
def get_project(project_id: int, db: Annotated[Session, Depends(get_db)]) -> RenovationProjectOut:
    return renovation_service.to_out(renovation_service.get_project(db, project_id))


@router.patch("/{project_id}", response_model=RenovationProjectOut, summary="更新项目登记信息")
def update_project(
    project_id: int, payload: RenovationProjectUpdate, db: Annotated[Session, Depends(get_db)]
) -> RenovationProjectOut:
    return renovation_service.to_out(
        renovation_service.update_project(db, project_id, payload)
    )


@router.get(
    "/{project_id}/transitions",
    response_model=list[TransitionOption],
    summary="可执行的项目流转动作",
)
def list_transitions(
    project_id: int, db: Annotated[Session, Depends(get_db)]
) -> list[TransitionOption]:
    project = renovation_service.get_project(db, project_id)
    return [TransitionOption(**option) for option in renovation_service.allowed_transitions(project)]


@router.post(
    "/{project_id}/transitions", response_model=RenovationProjectOut, summary="推进项目状态"
)
def change_status(
    project_id: int, payload: RenovationStatusUpdate, db: Annotated[Session, Depends(get_db)]
) -> RenovationProjectOut:
    return renovation_service.to_out(
        renovation_service.change_status(db, project_id, payload)
    )


@router.post(
    "/{project_id}/nodes", response_model=RenovationProjectOut, summary="登记改造进度节点"
)
def add_node(
    project_id: int, payload: RenovationNodeCreate, db: Annotated[Session, Depends(get_db)]
) -> RenovationProjectOut:
    return renovation_service.to_out(renovation_service.add_node(db, project_id, payload))


@router.patch(
    "/{project_id}/nodes/{node_id}",
    response_model=RenovationProjectOut,
    summary="登记/复验节点阶段验收结论",
)
def accept_node(
    project_id: int,
    node_id: int,
    payload: RenovationNodeAcceptance,
    db: Annotated[Session, Depends(get_db)],
) -> RenovationProjectOut:
    return renovation_service.to_out(
        renovation_service.accept_node(db, project_id, node_id, payload)
    )


@router.delete(
    "/{project_id}/nodes/{node_id}",
    response_model=RenovationProjectOut,
    summary="删除进度节点",
)
def delete_node(
    project_id: int, node_id: int, db: Annotated[Session, Depends(get_db)]
) -> RenovationProjectOut:
    return renovation_service.to_out(
        renovation_service.delete_node(db, project_id, node_id)
    )


@router.delete("/{project_id}", response_model=MessageOut, summary="删除改造项目")
def delete_project(project_id: int, db: Annotated[Session, Depends(get_db)]) -> MessageOut:
    renovation_service.delete_project(db, project_id)
    return MessageOut(message="删除成功")
