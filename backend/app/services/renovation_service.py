"""公厕改造项目业务逻辑。"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.constants import (
    ACTIVE_RENOVATION_STATUSES,
    RENOVATION_TRANSITION_ACTIONS,
    RENOVATION_TRANSITIONS,
    MilestoneConclusion,
    RenovationStatus,
    RestroomStatus,
)
from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.models import RenovationMilestone, RenovationProject, Restroom
from app.schemas.renovation import (
    RenovationCreate,
    RenovationMilestoneCreate,
    RenovationOut,
    RenovationStatusUpdate,
    RenovationUpdate,
)
from app.services import restroom_service

SORTABLE_FIELDS = {
    "code": RenovationProject.code,
    "approved_at": RenovationProject.approved_at,
    "planned_end": RenovationProject.planned_end,
    "budget": RenovationProject.budget,
    "status": RenovationProject.status,
    "progress": RenovationProject.progress,
    "created_at": RenovationProject.created_at,
}

# 项目档案流水类型
KIND_FLOW = "流程事件"
KIND_NODE = "节点进度"


def _next_code(db: Session) -> str:
    """生成形如 GZ-20240913-001 的项目编号。"""
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


def get_project(db: Session, project_id: int) -> RenovationProject:
    project = db.get(RenovationProject, project_id)
    if project is None:
        raise NotFoundError(f"改造项目 {project_id} 不存在")
    return project


def is_schedule_overdue(project: RenovationProject) -> bool:
    """计划完工时间已过且项目仍未完工归档。"""
    return (
        project.planned_end is not None
        and project.status in ACTIVE_RENOVATION_STATUSES
        and project.planned_end < datetime.now()
    )


def to_out(project: RenovationProject) -> RenovationOut:
    data = RenovationOut.model_validate(project)
    data.schedule_overdue = is_schedule_overdue(project)
    return data


def list_projects(
    db: Session,
    *,
    restroom_id: int | None = None,
    district: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "created_at",
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
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                RenovationProject.title.like(like),
                RenovationProject.code.like(like),
                RenovationProject.contractor.like(like),
                RenovationProject.reason.like(like),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    column = SORTABLE_FIELDS.get(sort_by, RenovationProject.created_at)
    stmt = stmt.order_by(
        column.desc() if order == "desc" else column.asc(), RenovationProject.id.desc()
    )
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def _append_flow(
    project: RenovationProject,
    *,
    action: str,
    operator: str,
    note: str | None,
    conclusion: str = "",
) -> None:
    """把流程事件写入项目档案流水，保证整份档案可追溯。"""
    project.milestones.append(
        RenovationMilestone(
            kind=KIND_FLOW,
            node=action,
            progress=None,
            conclusion=conclusion,
            operator=operator,
            note=note,
        )
    )


def create_project(db: Session, payload: RenovationCreate) -> RenovationProject:
    restroom = restroom_service.get_restroom(db, payload.restroom_id)
    active = db.scalar(
        select(func.count())
        .select_from(RenovationProject)
        .where(
            RenovationProject.restroom_id == restroom.id,
            RenovationProject.status.in_(ACTIVE_RENOVATION_STATUSES),
        )
    ) or 0
    if active:
        raise ConflictError("该公厕已存在进行中的改造项目，完工验收或取消后才能再次立项")

    project = RenovationProject(
        code=_next_code(db),
        restroom_id=restroom.id,
        title=payload.title,
        reason=payload.reason,
        approved_at=payload.approved_at or datetime.now(),
        contractor=payload.contractor,
        planned_start=payload.planned_start,
        planned_end=payload.planned_end,
        budget=payload.budget,
        remark=payload.remark,
        status=RenovationStatus.APPROVED.value,
    )
    _append_flow(project, action="项目立项", operator=payload.contractor, note=payload.reason)
    db.add(project)
    db.commit()
    db.refresh(project)
    restroom_service.touch(db, restroom.id)
    return project


def update_project(
    db: Session, project_id: int, payload: RenovationUpdate
) -> RenovationProject:
    project = get_project(db, project_id)
    if project.status not in ACTIVE_RENOVATION_STATUSES:
        raise DomainError(f"项目已{project.status}，档案已归档，不允许再修改")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(project, key, value.value if hasattr(value, "value") else value)
    if (
        project.planned_start is not None
        and project.planned_end is not None
        and project.planned_end <= project.planned_start
    ):
        raise DomainError("计划完工时间必须晚于计划开工时间")
    db.commit()
    db.refresh(project)
    return project


def allowed_transitions(project: RenovationProject) -> list[dict[str, str]]:
    return [
        {
            "status": target,
            "action": RENOVATION_TRANSITION_ACTIONS.get((project.status, target), "状态变更"),
        }
        for target in RENOVATION_TRANSITIONS.get(project.status, [])
    ]


def _restore_restroom_status(project: RenovationProject) -> None:
    """完工验收或项目取消后，把公厕从停用恢复为改造前的开放状态。"""
    restroom = project.restroom
    if restroom is None or restroom.status != RestroomStatus.CLOSED.value:
        return
    restroom.status = project.previous_restroom_status or RestroomStatus.NORMAL.value


def change_status(
    db: Session, project_id: int, payload: RenovationStatusUpdate
) -> RenovationProject:
    project = get_project(db, project_id)
    target = payload.to_status.value
    if target == project.status:
        raise DomainError(f"项目已处于「{target}」状态")
    allowed = RENOVATION_TRANSITIONS.get(project.status, [])
    if target not in allowed:
        raise DomainError(
            f"当前状态「{project.status}」不允许流转到「{target}」，可选："
            + ("、".join(allowed) if allowed else "无（项目已归档）")
        )

    from_status = project.status
    restroom = project.restroom
    if target == RenovationStatus.WORKING.value and from_status == RenovationStatus.APPROVED.value:
        # 开工：改造期间公厕自动转为停用，并记下改造前状态便于完工恢复
        if restroom is not None:
            project.previous_restroom_status = restroom.status
            restroom.status = RestroomStatus.CLOSED.value
        project.started_at = datetime.now()
    elif target == RenovationStatus.COMPLETED.value:
        # 完工验收通过：恢复公厕开放状态，项目进度记为 100%
        project.finished_at = datetime.now()
        project.progress = 100
        project.completion_conclusion = (
            payload.conclusion.value if payload.conclusion else MilestoneConclusion.PASSED.value
        )
        _restore_restroom_status(project)
    elif target == RenovationStatus.CANCELLED.value:
        # 取消：若改造已开始，同样需要恢复公厕开放状态
        _restore_restroom_status(project)

    project.status = target
    action = RENOVATION_TRANSITION_ACTIONS.get((from_status, target), "状态变更")
    _append_flow(
        project,
        action=action,
        operator=payload.operator,
        note=payload.remark,
        conclusion=project.completion_conclusion
        if target == RenovationStatus.COMPLETED.value
        else "",
    )
    db.commit()
    db.refresh(project)
    restroom_service.touch(db, project.restroom_id)
    return project


def add_milestone(
    db: Session, project_id: int, payload: RenovationMilestoneCreate
) -> RenovationProject:
    """按节点记录进度与阶段验收结论，仅改造中可上报。"""
    project = get_project(db, project_id)
    if project.status != RenovationStatus.WORKING.value:
        raise DomainError(f"项目当前状态为「{project.status}」，仅改造中可记录节点进度")
    project.milestones.append(
        RenovationMilestone(
            kind=KIND_NODE,
            node=payload.node,
            progress=payload.progress,
            conclusion=payload.conclusion.value,
            operator=payload.operator,
            note=payload.note,
        )
    )
    project.progress = payload.progress
    db.commit()
    db.refresh(project)
    restroom_service.touch(db, project.restroom_id)
    return project
