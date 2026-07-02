"""因子模块 schema."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginatedResponse, PaginationParams


class FactorBase(BaseModel):
    """因子基础字段."""

    name: str = Field(..., max_length=64, description="因子名称")
    category: str = Field(..., max_length=32, description="分类：valuation/growth/quality/technical/scale")
    description: Optional[str] = Field(None, description="因子描述")
    lookback: int = Field(0, ge=0, description="回看期")
    freq: str = Field("daily", description="频率：daily/quarterly/monthly")
    depends: Optional[str] = Field(None, description="数据依赖，逗号分隔")


class FactorCreate(FactorBase):
    """创建因子."""


class FactorUpdate(BaseModel):
    """更新因子."""

    category: Optional[str] = None
    description: Optional[str] = None
    lookback: Optional[int] = Field(None, ge=0)
    freq: Optional[str] = None
    depends: Optional[str] = None
    enabled: Optional[bool] = None


class FactorOut(FactorBase):
    """因子响应."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    enabled: bool
    display_name: Optional[str] = Field(None, description="显示名称")
    direction: int = Field(1, description="因子方向：1=正向，-1=负向")


class FactorListParams(PaginationParams):
    """因子列表查询参数."""

    category: Optional[str] = Field(None, description="按分类筛选")
    enabled: Optional[bool] = Field(None, description="按启用状态筛选")
    keyword: Optional[str] = Field(None, description="按名称模糊搜索")


class FactorValueOut(BaseModel):
    """因子值."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    date: date
    factor_name: str
    raw_value: Optional[float] = None
    neut_value: Optional[float] = None


class FactorValueQuery(BaseModel):
    """因子值查询参数."""

    factor_name: str = Field(..., description="因子名称")
    # 字段名避开 ``date``（与 datetime.date 同名会触发 pydantic 注解解析冲突）
    on_date: Optional[date] = Field(None, description="指定日期，不传则取最新")
    code: Optional[str] = Field(None, description="指定股票代码")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: int = Field(500, ge=1, le=10000)


class FactorEvaluateResult(BaseModel):
    """因子有效性评估结果（IC / ICIR / 分层收益）."""

    factor_name: str
    ic_mean: Optional[float] = Field(None, description="IC 均值")
    ic_std: Optional[float] = Field(None, description="IC 标准差")
    ir: Optional[float] = Field(None, description="ICIR")
    win_rate: Optional[float] = Field(None, description="IC 胜率")
    ic_series: Optional[List[dict]] = Field(None, description="IC 时间序列")
    layer_returns: Optional[List[float]] = Field(None, description="分层收益")
    effective: Optional[bool] = Field(None, description="是否有效")


class FactorListResponse(PaginatedResponse[FactorOut]):
    """因子分页响应."""
