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
    NodeAcceptance,
    RenovationStatus,
    RestroomGrade,
    RestroomStatus,
    Shift,
)
from app.models import Restroom
from app.schemas.inspection import InspectionCreate, InspectionItem
from app.schemas.issue import IssueCreate, IssueStatusUpdate
from app.schemas.renovation import (
    RenovationNodeAcceptance,
    RenovationNodeCreate,
    RenovationProjectCreate,
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

    seed_renovations(db, restrooms)

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


# (公厕序号, 施工单位, 现场负责人, 事由, 预算万元, 计划开工偏移天, 计划完工偏移天)
def seed_renovations(db: Session, restrooms: list) -> None:
    """写入 4 个不同阶段的改造项目，演示立项停用、节点验收、完工恢复与档案封存。"""
    rng = random.Random(RANDOM_SEED + 1)
    now = datetime.now()

    def d(offset: int) -> datetime:
        return now + timedelta(days=offset)

    def setup(idx: int, unit: str, manager: str, reason: str, budget: float,
              start_offset: int, end_offset: int, *, phone: str = ""):
        return renovation_service.create_project(
            db,
            RenovationProjectCreate(
                restroom_id=restrooms[idx].id,
                reason=reason,
                construction_unit=unit,
                project_manager=manager,
                contact_phone=phone or f"13{rng.randint(100000000, 999999999)}",
                setup_time=d(start_offset - 2),
                planned_start_date=(now + timedelta(days=start_offset)).date(),
                planned_end_date=(now + timedelta(days=end_offset)).date(),
                budget=budget,
            ),
        )

    def transition(project_id: int, target: RenovationStatus, operator: str, remark: str,
                   actual_cost: float | None = None) -> None:
        renovation_service.change_status(
            db,
            project_id,
            RenovationStatusUpdate(
                to_status=target, operator=operator, remark=remark, actual_cost=actual_cost
            ),
        )

    def node(project_id: int, title: str, offset: int, percent: int, operator: str,
             progress: str, accept: tuple[NodeAcceptance, str, str] | None = None) -> None:
        project = renovation_service.add_node(
            db,
            project_id,
            RenovationNodeCreate(
                title=title,
                node_date=(now + timedelta(days=offset)).date(),
                progress=progress,
                progress_percent=percent,
                operator=operator,
            ),
        )
        if accept is not None:
            result, opinion, acceptor = accept
            renovation_service.accept_node(
                db,
                project_id,
                project.nodes[-1].id,
                RenovationNodeAcceptance(result=result, opinion=opinion, acceptor=acceptor),
            )

    # 1) 人民广场公厕：60 天前立项，已竣工验收，公厕恢复正常开放（档案封存）
    p1 = setup(
        0, "城央建设工程有限公司", "林建华",
        "设施老化、给排水系统渗漏，按一类公厕标准整体提档升级，增设第三卫生间与母婴设施。",
        28.5, -58, -3,
    )
    transition(p1.id, RenovationStatus.PROCESSING, "林建华", "施工队进场，围挡封闭，公厕暂停使用")
    node(p1.id, "拆除与垃圾清运", -55, 100, "林建华", "旧洁具、隔断拆除完毕，建筑垃圾当日清运。",
         (NodeAcceptance.PASS, "拆除到位，现场安全文明施工达标。", "甲方代表周科"))
    node(p1.id, "水电管线改造", -42, 100, "林建华", "给排水管线、强弱电桥架全部更换并完成试压。",
         (NodeAcceptance.PASS, "试压合格，管线走向规范。", "监理吴工"))
    node(p1.id, "装饰装修", -22, 100, "林建华", "墙地砖铺贴、吊顶与隔断安装完成。",
         (NodeAcceptance.PASS, "平整度与空鼓检查合格。", "监理吴工"))
    node(p1.id, "洁具设备安装", -8, 100, "林建华", "感应洁具、新风系统、第三卫生间设施安装调试完成。",
         (NodeAcceptance.PASS, "设备运行正常，无障碍设施齐备。", "甲方代表周科"))
    transition(p1.id, RenovationStatus.REVIEWING, "林建华", "全部工程完工，申请竣工验收")
    transition(p1.id, RenovationStatus.ACCEPTED, "验收组周科",
               "竣工验收通过，工程质量合格，资料齐全，同意恢复开放。", actual_cost=26.8)

    # 2) 滨江公园公厕：施工中且已超过计划完工日期（演示工期超期），公厕停用
    p2 = setup(
        1, "绿苑市政工程公司", "高志远",
        "通风除臭效果差、洁具锈蚀，更换节能洁具并改造排风系统。",
        12.0, -25, -2,
    )
    transition(p2.id, RenovationStatus.PROCESSING, "高志远", "正式开工，现场封闭施工")
    node(p2.id, "拆除与管线探查", -23, 100, "高志远", "旧洁具拆除，地下管线探查完成。",
         (NodeAcceptance.PASS, "符合要求。", "监理吴工"))
    node(p2.id, "排风系统改造", -10, 70, "高志远", "新风机组已安装，风管安装进行中，因定制风管到货延迟工期顺延。",
         (NodeAcceptance.FAIL, "部分风管支吊架间距偏大，要求整改后复验。", "监理吴工"))

    # 3) 老城区第三小学旁公厕：原本即暂停使用，立项待施工（立项前状态被保存）
    setup(
        9, "老城区修缮队", "马德福",
        "屋面漏雨、墙面霉变，趁停用期间进行防水修缮与内墙翻新。",
        6.8, 2, 20,
    )

    # 4) 西城集贸市场公厕：已完工报验，等待竣工验收，公厕停用
    p4 = setup(
        4, "城央建设工程有限公司", "宋海峰",
        "人流量大导致地面排水不畅、蹲位不足，扩建蹲位并重做地面排水。",
        15.2, -30, -1,
    )
    transition(p4.id, RenovationStatus.PROCESSING, "宋海峰", "开工施工")
    node(p4.id, "地面破除与排水重做", -26, 100, "宋海峰", "排水沟重做、地面找坡完成。",
         (NodeAcceptance.PASS, "排水通畅，坡度符合设计。", "监理吴工"))
    node(p4.id, "隔断扩建与洁具安装", -8, 100, "宋海峰", "新增 2 个蹲位，洁具安装调试完成。",
         (NodeAcceptance.PASS, "安装牢固，试水无渗漏。", "甲方代表周科"))
    transition(p4.id, RenovationStatus.REVIEWING, "宋海峰", "工程完工，报验竣工验收")
