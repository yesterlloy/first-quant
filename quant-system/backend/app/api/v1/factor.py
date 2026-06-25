"""因子路由：CRUD、因子值查询、有效性评估."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.factor import (
    FactorCreate,
    FactorEvaluateResult,
    FactorListResponse,
    FactorOut,
    FactorUpdate,
    FactorValueOut,
)
from app.services import factor_service

router = APIRouter()


@router.get("", response_model=ApiResponse[FactorListResponse])
def list_factors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    category: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """分页查询因子列表."""
    from app.schemas.factor import FactorListParams

    params = PaginationParams(page=page, page_size=page_size)
    fp = FactorListParams(
        page=page, page_size=page_size, category=category, enabled=enabled, keyword=keyword
    )
    items, total = factor_service.list_factors(db, fp)
    return ApiResponse.success(
        data=PaginatedResponse[FactorOut].create(
            items=[FactorOut.model_validate(f) for f in items],
            total=total,
            params=params,
        )
    )


@router.get("/{name}", response_model=ApiResponse[FactorOut])
def get_factor(name: str, db: Session = Depends(get_db)):
    """查询单个因子详情."""
    factor = factor_service.get_factor(db, name)
    return ApiResponse.success(data=FactorOut.model_validate(factor))


@router.post("", response_model=ApiResponse[FactorOut], status_code=status.HTTP_201_CREATED)
def create_factor(
    factor_in: FactorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """创建因子（需登录）."""
    factor = factor_service.create_factor(db, factor_in)
    return ApiResponse.success(data=FactorOut.model_validate(factor), message="创建成功")


@router.put("/{name}", response_model=ApiResponse[FactorOut])
def update_factor(
    name: str,
    factor_in: FactorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """更新因子（需登录）."""
    factor = factor_service.update_factor(db, name, factor_in)
    return ApiResponse.success(data=FactorOut.model_validate(factor), message="更新成功")


@router.delete("/{name}", response_model=ApiResponse[None])
def delete_factor(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除因子（需登录）."""
    factor_service.delete_factor(db, name)
    return ApiResponse.success(message="删除成功")


@router.get("/{name}/values", response_model=ApiResponse[list[FactorValueOut]])
def get_factor_values(
    name: str,
    date: Optional[date] = Query(None, description="指定日期"),
    code: Optional[str] = Query(None, description="指定股票"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    """查询因子值."""
    from app.schemas.factor import FactorValueQuery

    query = FactorValueQuery(
        factor_name=name,
        on_date=date,
        code=code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    items = factor_service.get_factor_values(db, query)
    return ApiResponse.success(data=[FactorValueOut.model_validate(v) for v in items])


@router.get("/{name}/evaluate", response_model=ApiResponse[FactorEvaluateResult])
def evaluate_factor(
    name: str,
    forward_period: Optional[int] = Query(None, description="前瞻收益期，默认取配置"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """评估因子有效性（IC / ICIR / IC 胜率）."""
    result = factor_service.evaluate_factor(
        db, name, forward_period=forward_period, start_date=start_date, end_date=end_date
    )
    return ApiResponse.success(data=result)
