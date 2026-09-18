"""公厕改造项目跟踪业务逻辑。"""

from datetime import date, datetime, time

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    OPEN_RENOVATION_STATUSES,
    RENOVATION_TRANSITIONS,
    RENOVATION_TRANSITION_ACTIONS,
    RenovationStatus,
    RestroomStatus,
)
from app.core.exceptions import DomainError, NotFoundError
from app.models import RenovationNode, RenovationProject, RenovationRecord, Restroom
from app.schemas.renovation import (
    RenovationNodeAcceptance,
    RenovationNodeCreate,
    RenovationProjectCreate,
    RenovationProjectOut,
    RenovationProjectUpdate,
    RenovationStatusUpdate,
)
from app.services import restroom_service

SORTABLE_FIELDS = {
    "setup_time": RenovationProject.setup_time,
    "planned_end_date": RenovationProject.planned_end_date,
    "budget": RenovationProject.budget,
    "status": RenovationProject.status,
    "code": RenovationProject.code,
    "updated_at": RenovationProject.updated_at,
}


def _next_code(db: Session) -> str:
    prefix = datetime.now().strftime("GZ-%Y%m%d")
    seq = (
        db.scalar(
            select(func.count())
            .select_from(RenovationProject)
            .where(RenovationProject.code.like(f"{prefix}-%"))
        )
        or 0
    ) + 1
    while True:
        code = f"{prefix}-{seq:03d}"
        if not db.scalar(select(RenovationProject.id).where(RenovationProject.code == code)):
            return code
        seq += 1


def _values(data: dict) -> dict:
    return {key: (value.value if hasattr(value, "value") else value) for key, value in data.items()}


def get_project(db: Session, project_id: int) -> RenovationProject:
    project = db.get(RenovationProject, project_id)
    if project is None:
        raise NotFoundError(f"改造项目 {project_id} 不存在")
    return project


def get_node(db: Session, project: RenovationProject, node_id: int) -> RenovationNode:
    node = db.get(RenovationNode, node_id)
    if node is None or node.project_id != project.id:
        raise NotFoundError(f"进度节点 {node_id} 不存在")
    return node


def to_out(project: RenovationProject) -> RenovationProjectOut:
    return RenovationProjectOut.model_validate(project)


def _ensure_active(project: RenovationProject) -> None:
    if project.status == RenovationStatus.ACCEPTED.value:
        raise DomainError("项目已竣工验收并封存，无法修改档案")


def list_projects(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    status: str | None = None,
    open_only: bool = False,
    delayed: bool | None = None,
    keyword: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "setup_time",
    order: str = "desc",
) -> tuple[list[RenovationProject], int]:
    stmt = select(RenovationProject)
    if district:
        stmt = stmt.join(Restroom, Restroom.id == RenovationProject.restroom_id).where(
            Restroom.district == district
        )
    if restroom_id:
        stmt = stmt.where(RenovationProject.restroom_id == restroom_id)
    if status:
        stmt = stmt.where(RenovationProject.status == status)
    if open_only:
        stmt = stmt.where(RenovationProject.status.in_(OPEN_RENOVATION_STATUSES))
    if date_from:
        stmt = stmt.where(RenovationProject.setup_time >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(RenovationProject.setup_time <= datetime.combine(date_to, time.max))
    if delayed is True:
        stmt = stmt.where(
            RenovationProject.planned_end_date.is_not(None),
            RenovationProject.planned_end_date < date.today(),
            RenovationProject.status.in_(OPEN_RENOVATION_STATUSES),
        )
    elif delayed is False:
        stmt = stmt.where(
            or_(
                RenovationProject.planned_end_date.is_(None),
                RenovationProject.planned_end_date >= date.today(),
                RenovationProject.status == RenovationStatus.ACCEPTED.value,
            )
        )
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                RenovationProject.reason.like(like),
                RenovationProject.code.like(like),
                RenovationProject.construction_unit.like(like),
                RenovationProject.project_manager.like(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, RenovationProject.setup_time)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), RenovationProject.id.desc())
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def create_project(db: Session, payload: RenovationProjectCreate) -> RenovationProject:
    restroom = restroom_service.get_restroom(db, payload.restroom_id)
    active_count = db.scalar(
        select(func.count())
        .select_from(RenovationProject)
        .where(
            RenovationProject.restroom_id == payload.restroom_id,
            RenovationProject.status.in_(OPEN_RENOVATION_STATUSES),
        )
    ) or 0
    if active_count:
        raise DomainError("该公厕已有进行中的改造项目，不能重复立项")

    data = _values(payload.model_dump(exclude={"setup_time"}))
    project = RenovationProject(
        code=_next_code(db),
        setup_time=payload.setup_time or datetime.now(),
        status=RenovationStatus.PENDING.value,
        previous_restroom_status=restroom.status,
        **data,
    )
    # 改造期间公厕自动停用
    restroom.status = RestroomStatus.CLOSED.value
    project.records.append(
        RenovationRecord(
            action="立项登记",
            from_status="",
            to_status=RenovationStatus.PENDING.value,
            operator=payload.project_manager or "项目管理员",
            remark=f"立项登记，公厕暂停使用；改造事由：{payload.reason}",
        )
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    restroom_service.touch(db, project.restroom_id)
    return project


def update_project(db: Session, project_id: int, payload: RenovationProjectUpdate) -> RenovationProject:
    project = get_project(db, project_id)
    _ensure_active(project)
    data = _values(payload.model_dump(exclude_unset=True))
    # 合并后再校验日期顺序，允许只提交其中一个日期
    start = data.get("planned_start_date", project.planned_start_date)
    end = data.get("planned_end_date", project.planned_end_date)
    if start is not None and end is not None and end < start:
        raise DomainError("计划完工日期不能早于计划开工日期")
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def allowed_transitions(project: RenovationProject) -> list[dict[str, str]]:
    return [
        {"status": target, "action": RENOVATION_TRANSITION_ACTIONS.get((project.status, target), "状态变更")}
        for target in RENOVATION_TRANSITIONS.get(project.status, [])
    ]


def change_status(db: Session, project_id: int, payload: RenovationStatusUpdate) -> RenovationProject:
    project = get_project(db, project_id)
    target = payload.to_status.value
    if target == project.status:
        raise DomainError(f"项目已处于「{target}」状态")
    allowed = RENOVATION_TRANSITIONS.get(project.status, [])
    if target not in allowed:
        raise DomainError(
            f"当前状态「{project.status}」不允许流转到「{target}」，可选："
            + ("、".join(allowed) if allowed else "无（项目已封存）")
        )

    from_status = project.status
    project.status = target
    if payload.to_status == RenovationStatus.PROCESSING and project.actual_start_time is None:
        project.actual_start_time = datetime.now()
    if payload.to_status == RenovationStatus.ACCEPTED:
        # 竣工验收通过：恢复公厕立项前状态并封存档案
        restroom = restroom_service.get_restroom(db, project.restroom_id)
        restroom.status = project.previous_restroom_status or RestroomStatus.NORMAL.value
        project.accepted_at = datetime.now()
        project.accepted_opinion = payload.remark
        if payload.actual_cost is not None:
            project.actual_cost = payload.actual_cost
    project.records.append(
        RenovationRecord(
            action=RENOVATION_TRANSITION_ACTIONS.get((from_status, target), "状态变更"),
            from_status=from_status,
            to_status=target,
            operator=payload.operator,
            remark=payload.remark,
        )
    )
    db.commit()
    db.refresh(project)
    restroom_service.touch(db, project.restroom_id)
    return project


def add_node(db: Session, project_id: int, payload: RenovationNodeCreate) -> RenovationProject:
    project = get_project(db, project_id)
    if project.status != RenovationStatus.PROCESSING.value:
        raise DomainError("仅「施工中」的项目可以登记进度节点")
    project.nodes.append(
        RenovationNode(
            title=payload.title,
            node_date=payload.node_date,
            progress=payload.progress,
            progress_percent=payload.progress_percent,
            operator=payload.operator,
        )
    )
    project.records.append(
        RenovationRecord(
            action="进度节点",
            from_status=project.status,
            to_status=project.status,
            operator=payload.operator or "施工单位",
            remark=f"登记节点「{payload.title}」",
        )
    )
    db.commit()
    db.refresh(project)
    return project


def accept_node(
    db: Session, project_id: int, node_id: int, payload: RenovationNodeAcceptance
) -> RenovationProject:
    project = get_project(db, project_id)
    _ensure_active(project)
    if project.status not in (
        RenovationStatus.PROCESSING.value,
        RenovationStatus.REVIEWING.value,
    ):
        raise DomainError("项目尚未开工，无法登记阶段验收")
    node = get_node(db, project, node_id)
    node.acceptance_result = payload.result.value
    node.acceptance_opinion = payload.opinion
    node.acceptor = payload.acceptor
    node.accepted_at = datetime.now()
    project.records.append(
        RenovationRecord(
            action="阶段验收",
            from_status=project.status,
            to_status=project.status,
            operator=payload.acceptor,
            remark=f"节点「{node.title}」验收结论：{payload.result.value}",
        )
    )
    db.commit()
    db.refresh(project)
    return project


def delete_node(db: Session, project_id: int, node_id: int) -> RenovationProject:
    project = get_project(db, project_id)
    if project.status != RenovationStatus.PROCESSING.value:
        raise DomainError("仅「施工中」的项目可以删除进度节点")
    node = get_node(db, project, node_id)
    db.delete(node)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int) -> None:
    """删除进行中的项目，并恢复公厕立项前状态；已封存项目不允许删除。"""
    project = get_project(db, project_id)
    _ensure_active(project)
    restroom = db.get(Restroom, project.restroom_id)
    if restroom is not None and restroom.status == RestroomStatus.CLOSED.value:
        restroom.status = project.previous_restroom_status or RestroomStatus.NORMAL.value
    db.delete(project)
    db.commit()
