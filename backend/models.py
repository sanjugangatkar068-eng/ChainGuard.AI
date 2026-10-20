from typing import Literal

from pydantic import BaseModel, Field


class Supplier(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    tier: int = Field(default=1, ge=1, le=5)
    country: str = Field(default="Unknown", max_length=80)
    single_source: bool = False
    lead_time_days: int = Field(default=14, ge=0, le=365)
    spend_usd: float = Field(default=0, ge=0)


class DisruptionRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)

    disruption_type: Literal[
        "port_closure",
        "weather",
        "tariff_change",
        "supplier_outage",
        "port_congestion",
        "demand_spike",
        "other"
    ]

    location: str = Field(max_length=160)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    description: str = Field(default="", max_length=2000)
    affected_supplier: str | None = Field(default=None, max_length=160)
    delay_days: int = Field(default=5, ge=0, le=90)
    tariff_percent: float = Field(default=0, ge=0, le=500)
    estimated_loss_usd: float = Field(default=0, ge=0)


class ScenarioRequest(BaseModel):
    disruption_id: int | None = None
    demand_units_per_day: int = Field(default=20, ge=0)
    current_inventory: int = Field(default=240, ge=0)
    lead_time_days: int = Field(default=4, ge=0)
    safety_stock: int = Field(default=40, ge=0)
    unit_cost_usd: float = Field(default=25, ge=0)
    expedite_cost_usd: float = Field(default=500, ge=0)
    reroute_cost_usd: float = Field(default=1200, ge=0)
    max_budget_usd: float = Field(default=10000, ge=0)
    suppliers: list[Supplier] = Field(default_factory=list)


class SupplierRiskRequest(BaseModel):
    disruption_id: int | None = None
    suppliers: list[Supplier] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=2, max_length=120)
    comments: str = Field(default="", max_length=2000)
