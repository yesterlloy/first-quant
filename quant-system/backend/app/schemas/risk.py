"""风控相关 Schema."""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RiskRuleOut(BaseModel):
    """风控规则输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_name: str
    rule_type: str
    level: str  # info/warning/block
    params: Optional[Dict[str, Any]] = None
    enabled: bool
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("params", mode="before")
    @classmethod
    def parse_params(cls, v):
        """解析数据库中的 JSON 字符串."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class RiskRuleCreate(BaseModel):
    """创建风控规则."""

    rule_name: str = Field(..., max_length=100, description="规则名称")
    rule_type: str = Field(..., max_length=64, description="规则类型/类名")
    level: str = Field("warning", description="触发等级：info/warning/block")
    params: Optional[Dict[str, Any]] = Field(None, description="规则参数")
    enabled: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="规则描述")


class RiskRuleUpdate(BaseModel):
    """更新风控规则."""

    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    level: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None


class RiskEventOut(BaseModel):
    """风控事件输出."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    level: str
    type: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    @field_validator("details", mode="before")
    @classmethod
    def parse_details(cls, v):
        """解析数据库中的 JSON 字符串."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class RiskCheckRequest(BaseModel):
    """风控检查请求."""

    action: str = Field(..., description="操作类型：buy/sell/portfolio")
    code: Optional[str] = Field(None, description="股票代码")
    shares: Optional[int] = Field(None, gt=0, description="数量")
    price: Optional[float] = Field(None, gt=0, description="价格")


class RiskCheckResult(BaseModel):
    """风控检查结果."""

    passed: bool
    level: str
    triggered_rules: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class RiskStatsOut(BaseModel):
    """风控统计."""

    total_events: int = 0
    today_events: int = 0
    warning_count: int = 0
    block_count: int = 0
    total_rules: int = 0
    enabled_rules: int = 0
    top_triggers: List[Dict[str, Any]] = Field(default_factory=list)
