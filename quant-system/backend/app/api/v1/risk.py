"""风控 API：规则管理、事件日志、风险检查."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.risk import (
    RiskCheckRequest,
    RiskCheckResult,
    RiskEventOut,
    RiskRuleCreate,
    RiskRuleOut,
    RiskRuleUpdate,
    RiskStatsOut,
)
from app.services import risk_service

router = APIRouter(prefix="/risk", tags=["风控"])


# ========== 风控规则管理 ==========

@router.get("/rules", response_model=ApiResponse[PaginatedResponse[RiskRuleOut]])
def list_rules(
    level: Optional[str] = Query(None, description="等级筛选：info/warning/block"),
    enabled: Optional[bool] = Query(None, description="是否启用"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取风控规则列表."""
    from app.schemas.common import PaginationParams
    params = PaginationParams(page=page, page_size=page_size)
    items, total = risk_service.list_rules(
        db, level=level, enabled=enabled, skip=(page - 1) * page_size, limit=page_size
    )
    return ApiResponse.success(
        data=PaginatedResponse[RiskRuleOut].create(
            items=items,
            total=total,
            params=params,
        )
    )


@router.get("/rules/{rule_id}", response_model=ApiResponse[RiskRuleOut])
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单个风控规则详情."""
    rule = risk_service.get_rule(db, rule_id)
    return ApiResponse.success(data=rule)


@router.post("/rules", response_model=ApiResponse[RiskRuleOut], status_code=status.HTTP_201_CREATED)
def create_rule(
    rule_in: RiskRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建风控规则."""
    rule = risk_service.create_rule(db, rule_in)
    return ApiResponse.success(data=rule, message="规则创建成功")


@router.put("/rules/{rule_id}", response_model=ApiResponse[RiskRuleOut])
def update_rule(
    rule_id: int,
    rule_in: RiskRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新风控规则."""
    rule = risk_service.update_rule(db, rule_id, rule_in)
    return ApiResponse.success(data=rule, message="规则更新成功")


@router.delete("/rules/{rule_id}", response_model=ApiResponse[None])
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除风控规则."""
    risk_service.delete_rule(db, rule_id)
    return ApiResponse.success(message="规则删除成功")


@router.post("/rules/{rule_id}/toggle", response_model=ApiResponse[RiskRuleOut])
def toggle_rule(
    rule_id: int,
    enabled: bool = Query(..., description="是否启用"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """启用/禁用风控规则."""
    rule = risk_service.toggle_rule(db, rule_id, enabled)
    status_text = "启用" if enabled else "禁用"
    return ApiResponse.success(data=rule, message=f"规则已{status_text}")


# ========== 风控事件管理 ==========

@router.get("/events", response_model=ApiResponse[PaginatedResponse[RiskEventOut]])
def list_events(
    level: Optional[str] = Query(None, description="等级筛选：info/warning/block"),
    event_type: Optional[str] = Query(None, description="事件类型筛选"),
    code: Optional[str] = Query(None, description="股票代码筛选"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取风控事件列表."""
    from app.schemas.common import PaginationParams
    params = PaginationParams(page=page, page_size=page_size)
    items, total = risk_service.list_events(
        db,
        level=level,
        event_type=event_type,
        code=code,
        start_date=start_date,
        end_date=end_date,
        skip=(page - 1) * page_size,
        limit=page_size,
    )
    return ApiResponse.success(
        data=PaginatedResponse[RiskEventOut].create(
            items=items,
            total=total,
            params=params,
        )
    )


@router.get("/events/{event_id}", response_model=ApiResponse[RiskEventOut])
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取单个风控事件详情."""
    event = risk_service.get_event(db, event_id)
    return ApiResponse.success(data=event)


# ========== 风控检查 ==========

@router.post("/check", response_model=ApiResponse[RiskCheckResult])
def check_risk(
    request: RiskCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """执行风控检查（下单前调用）."""
    result = risk_service.check_risk(
        db,
        action=request.action,
        code=request.code,
        shares=request.shares,
        price=request.price,
    )
    return ApiResponse.success(data=result)


# ========== 风控统计 ==========

@router.get("/stats", response_model=ApiResponse[RiskStatsOut])
def get_risk_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取风控统计数据."""
    stats = risk_service.get_risk_stats(db)
    return ApiResponse.success(data=stats)


@router.post("/init-default-rules", response_model=ApiResponse[None])
def init_default_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """初始化默认风控规则（仅首次运行需要）."""
    risk_service.init_default_rules(db)
    return ApiResponse.success(message="默认风控规则初始化完成")
