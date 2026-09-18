"""演示数据生成：首次启动时写入，便于快速体验各模块。"""

import random
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    INSPECTION_CHECK_ITEMS,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    MilestoneConclusion,
    RenovationStatus,
    RestroomGrade,
    RestroomStatus,
    Shift,
)
from app.models import Restroom
from app.schemas.inspection import InspectionCreate, InspectionItem
from app.schemas.issue import IssueCreate, IssueStatusUpdate
from app.schemas.renovation import (
    RenovationCreate,
    RenovationMilestoneCreate,
    RenovationStatusUpdate,
)
from app.schemas.restroom import RestroomCreate
from app.services import inspection_service, issue_service, renovation_service, restroom_service

RANDOM_SEED = 20240913

RESTROOM_SPECS = [
    ("人民广场公共厕所", "城东区", "人民广场东侧 50 米", RestroomGrade.FIRST, RestroomStatus.NORMAL, "王秀兰", 12, 6, True),
    ("滨江公园公共厕所", "城东区", "滨江公园 3 号入口", RestroomGrade.SECOND, RestroomStatus.NORMAL, "李国强", 8, 4, True),
    ("和平路公共厕所", "城东区", "和平路与解放街交叉口", RestroomGrade.THIRD, RestroomStatus.MAINTENANCE, "赵敏", 4, 2, False),
    ("火车站南广场公共厕所", "城西区", "火车站南广场西侧", RestroomGrade.FIRST, RestroomStatus.NORMAL, "陈志远", 16, 8, True),
    ("西城集贸市场公共厕所", "城西区", "西城集贸市场北门", RestroomGrade.SECOND, RestroomStatus.NORMAL, "刘桂芳", 10, 4, False),
    ("文化路步行街公共厕所", "城西区", "文化路步行街中段", RestroomGrade.SECOND, RestroomStatus.NORMAL, "孙鹏", 9, 5, True),
    ("滨江新区体育中心公共厕所", "滨江新区", "体育中心东看台下", RestroomGrade.FIRST, RestroomStatus.NORMAL, "周晓燕", 14, 7, True),
    ("滨江新区政务中心公共厕所", "滨江新区", "政务服务中心一楼", RestroomGrade.SECOND, RestroomStatus.NORMAL, "吴建华", 8, 4, True),
    ("老城隍庙公共厕所", "老城区", "城隍庙街 12 号", RestroomGrade.THIRD, RestroomStatus.NORMAL, "郑淑珍", 5, 2, False),
    ("老城区第三小学旁公共厕所", "老城区", "第三小学东侧巷道", RestroomGrade.THIRD, RestroomStatus.CLOSED, "何伟", 4, 2, False),
]

INSPECTORS = ["张伟", "刘洋", "胡明月", "邓晨曦", "马晓峰", "杨柳"]
MANAGERS = ["王秀兰", "李国强", "陈志远", "刘桂芳", "周晓燕", "吴建华", "郑淑珍", "孙鹏"]

ISSUE_TEMPLATES = {
    IssueCategory.CLEANING: [
        "地面存在明显污渍未及时清理",
        "蹲位清洁不彻底，存在残留",
        "垃圾篓内垃圾未及时清运",
    ],
    IssueCategory.FACILITY: [
        "水龙头漏水，需更换阀芯",
        "感应冲水器失灵，无法自动冲水",
        "隔间门锁损坏无法反锁",
    ],
    IssueCategory.ODOR: [
        "公厕内异味明显，通风效果差",
        "排风扇停转导致异味积聚",
    ],
    IssueCategory.CONSUMABLE: [
        "洗手液未及时补充",
        "纸巾盒空置，未补充厕纸",
    ],
    IssueCategory.SAFETY: [
        "地面湿滑未放置防滑警示牌",
        "照明灯具损坏，夜间存在安全隐患",
    ],
    IssueCategory.OTHER: [
        "无障碍扶手松动需加固",
        "标识牌褪色需更换",
    ],
}

CATEGORY_BY_ITEM = {
    "地面与台阶清洁": IssueCategory.CLEANING,
    "便池蹲位清洁": IssueCategory.CLEANING,
    "洗手台与镜面": IssueCategory.CLEANING,
    "通风除臭": IssueCategory.ODOR,
    "耗材补充": IssueCategory.CONSUMABLE,
    "垃圾清运": IssueCategory.CLEANING,
    "工具与标识摆放": IssueCategory.OTHER,
    "墙面门窗卫生": IssueCategory.CLEANING,
}


def _build_items(rng: random.Random, quality: float) -> list[InspectionItem]:
    items: list[InspectionItem] = []
    for name in INSPECTION_CHECK_ITEMS:
        score = quality + rng.uniform(-1.6, 1.4)
        items.append(InspectionItem(name=name, score=max(0, min(10, round(score)))))
    return items


def _pick_problem(items: list[InspectionItem]) -> str | None:
    """找出最需要整改的检查项：优先取不合格项，否则取得分最低的一项。"""
    if not items:
        return None
    problems = [item for item in items if item.score < 6]
    pool = problems or items
    return min(pool, key=lambda item: item.score).name


def seed_database(db: Session, *, reset: bool = False) -> int:
    """写入演示数据，返回新增的问题条数；已有数据时默认跳过。"""
    existing = db.scalar(select(func.count()).select_from(Restroom)) or 0
    if existing and not reset:
        return 0

    rng = random.Random(RANDOM_SEED)
    now = datetime.now()

    restrooms = [
        restroom_service.create_restroom(
            db,
            RestroomCreate(
                name=name,
                district=district,
                address=address,
                grade=grade,
                status=status,
                manager=manager,
                manager_phone=f"13{rng.randint(100000000, 999999999)}",
                stall_count=stalls,
                basin_count=basins,
                has_accessible=accessible,
                open_hours="06:00-22:30" if grade == RestroomGrade.FIRST else "06:30-21:30",
            ),
        )
        for name, district, address, grade, status, manager, stalls, basins, accessible in RESTROOM_SPECS
    ]

    quality_by_restroom = {room.id: rng.uniform(7.4, 9.8) for room in restrooms}
    inspection_ids: list[tuple[int, int]] = []  # (restroom_id, inspection_id)

    for offset in range(13, -1, -1):
        day = now - timedelta(days=offset)
        for room in restrooms:
            if room.status == RestroomStatus.CLOSED:
                continue
            if rng.random() < 0.3:
                continue
            quality = quality_by_restroom[room.id] + rng.uniform(-1.0, 0.6)
            if rng.random() < 0.18:
                quality -= 2.6
            items = _build_items(rng, quality)
            inspection = inspection_service.create_inspection(
                db,
                InspectionCreate(
                    restroom_id=room.id,
                    inspector=rng.choice(INSPECTORS),
                    shift=rng.choice(list(Shift)),
                    inspect_time=day.replace(
                        hour=rng.choice([8, 10, 14, 16, 19]), minute=rng.choice([5, 20, 35, 50])
                    ),
                    items=items,
                    remark=None,
                ),
            )
            inspection_ids.append((room.id, inspection.id))

    created = 0
    for restroom_id, inspection_id in inspection_ids:
        summary = inspection_service.get_inspection(db, inspection_id)
        if summary.result != "发现问题" or rng.random() > 0.75:
            continue
        problem_item = _pick_problem([InspectionItem(**item) for item in summary.items])
        category = CATEGORY_BY_ITEM.get(problem_item or "", IssueCategory.OTHER)
        title = rng.choice(ISSUE_TEMPLATES[category])
        severity = (
            IssueSeverity.URGENT
            if category in (IssueCategory.SAFETY, IssueCategory.FACILITY) and rng.random() < 0.3
            else rng.choice([IssueSeverity.NORMAL, IssueSeverity.SERIOUS])
        )
        age_days = (now - summary.inspect_time).days
        deadline = summary.inspect_time + timedelta(
            days=1 if severity == IssueSeverity.URGENT else 3
        )
        issue = issue_service.create_issue(
            db,
            IssueCreate(
                restroom_id=restroom_id,
                inspection_id=inspection_id,
                title=title,
                description=f"巡查得分 {summary.score} 分（{summary.grade}），检查项「{problem_item}」不达标，请安排整改。",
                category=category,
                severity=severity,
                reporter=summary.inspector,
                assignee=rng.choice(MANAGERS),
                deadline=deadline,
                initial_remark="由保洁巡查自动生成的问题工单",
            ),
        )
        created += 1
        _advance_issue(db, issue.id, age_days, rng)

    _seed_renovations(db, restrooms, now)

    return created


def _advance_issue(db: Session, issue_id: int, age_days: int, rng: random.Random) -> None:
    """按问题存在时长模拟整改进度，让看板呈现多种状态。"""
    steps: list[tuple[str, str, str]] = []
    if age_days >= 1:
        steps.append(
            (
                IssueStatus.PROCESSING.value,
                "街办保洁队",
                "已派单至保洁班组，安排当日整改",
            )
        )
    if age_days >= 3:
        steps.append(
            (
                IssueStatus.REVIEWING.value,
                "整改责任人",
                "整改完成，提交巡查员验收",
            )
        )
    if age_days >= 5 and rng.random() < 0.75:
        steps.append((IssueStatus.DONE.value, "巡查员", "现场复核通过，问题已闭环"))
    if age_days >= 8 and rng.random() < 0.6:
        steps.append((IssueStatus.CLOSED.value, "值班长", "归档关闭"))

    for target, operator, remark in steps:
        try:
            issue_service.change_status(
                db,
                issue_id,
                IssueStatusUpdate(to_status=IssueStatus(target), operator=operator, remark=remark),
            )
        except Exception:  # noqa: BLE001  演示数据允许跳过不合法的流转
            break


def _seed_renovations(db: Session, restrooms: list[Restroom], now: datetime) -> None:
    """写入两个演示改造项目：一个已完工归档，一个改造中（公厕联动停用）。"""

    def backdate(project, days_ago: int, *fields: str) -> None:
        """把最近一条档案流水及项目时间字段回拨到 days_ago 天前，让演示数据更真实。"""
        stamp = now - timedelta(days=days_ago)
        project.milestones[-1].created_at = stamp
        for field in fields:
            setattr(project, field, stamp)
        db.commit()
        db.refresh(project)

    # 项目一：老城隍庙公厕综合改造，已完工验收，档案完整保留
    temple = restrooms[8]
    done = renovation_service.create_project(
        db,
        RenovationCreate(
            restroom_id=temple.id,
            title="老城隍庙公厕老旧设施综合改造",
            reason="建厕超过 15 年，洁具老化、排水不畅，群众反映强烈，列入年度民生实事改造计划。",
            approved_at=now - timedelta(days=90),
            contractor="市建工集团第三工程公司",
            planned_start=now - timedelta(days=85),
            planned_end=now - timedelta(days=22),
            budget=46.5,
            remark="改造期间引导市民使用城隍庙街临时公厕",
        ),
    )
    backdate(done, 90)
    done = renovation_service.change_status(
        db,
        done.id,
        RenovationStatusUpdate(
            to_status=RenovationStatus.WORKING, operator="项目管理办公室", remark="施工围挡已搭设，正式开工"
        ),
    )
    backdate(done, 85, "started_at")
    for node, progress, conclusion, days, note in [
        ("拆除清运", 20, MilestoneConclusion.PASSED, 76, "老旧洁具与隔断拆除完毕，建渣清运完成"),
        ("土建施工", 45, MilestoneConclusion.PASSED, 64, "墙地面基层处理完成"),
        ("水电改造", 65, MilestoneConclusion.CONDITIONAL, 52, "给排水管线更换完成，两处接口渗漏已要求返工"),
        ("装饰装修", 85, MilestoneConclusion.PASSED, 38, "墙地砖铺贴与吊顶完成"),
        ("设备安装", 100, MilestoneConclusion.PASSED, 28, "感应洁具、无障碍扶手安装调试完成"),
    ]:
        done = renovation_service.add_milestone(
            db,
            done.id,
            RenovationMilestoneCreate(
                node=node, progress=progress, conclusion=conclusion, operator="监理单位", note=note
            ),
        )
        backdate(done, days)
    done = renovation_service.change_status(
        db,
        done.id,
        RenovationStatusUpdate(
            to_status=RenovationStatus.ACCEPTANCE, operator="市建工集团第三工程公司", remark="合同范围内工程全部完成，申请完工验收"
        ),
    )
    backdate(done, 24)
    done = renovation_service.change_status(
        db,
        done.id,
        RenovationStatusUpdate(
            to_status=RenovationStatus.COMPLETED,
            operator="环卫所验收组",
            conclusion=MilestoneConclusion.PASSED,
            remark="现场验收合格，公厕恢复开放",
        ),
    )
    backdate(done, 20, "finished_at")

    # 项目二：第三小学旁公厕无障碍提升改造，改造中，公厕联动停用
    school = restrooms[9]
    working = renovation_service.create_project(
        db,
        RenovationCreate(
            restroom_id=school.id,
            title="第三小学旁公厕无障碍设施提升改造",
            reason="缺少无障碍通道与扶手，上下学高峰使用不便，家长多次投诉。",
            approved_at=now - timedelta(days=25),
            contractor="新城市政园林工程有限公司",
            planned_start=now - timedelta(days=20),
            planned_end=now + timedelta(days=10),
            budget=18.8,
        ),
    )
    backdate(working, 25)
    working = renovation_service.change_status(
        db,
        working.id,
        RenovationStatusUpdate(
            to_status=RenovationStatus.WORKING, operator="项目管理办公室", remark="进场施工，公厕暂停使用"
        ),
    )
    backdate(working, 20, "started_at")
    for node, progress, conclusion, days, note in [
        ("拆除清运", 30, MilestoneConclusion.PASSED, 15, "原有台阶与旧洁具拆除完成"),
        ("土建施工", 55, MilestoneConclusion.CONDITIONAL, 6, "无障碍坡道浇筑完成，坡度复测合格后进入下一工序"),
    ]:
        working = renovation_service.add_milestone(
            db,
            working.id,
            RenovationMilestoneCreate(
                node=node, progress=progress, conclusion=conclusion, operator="监理单位", note=note
            ),
        )
        backdate(working, days)
