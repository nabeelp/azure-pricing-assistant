"""Shared data models for orchestrator flows."""

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class BOMItem:
    serviceName: str
    sku: str
    quantity: float
    region: str
    armRegionName: str
    hours_per_month: float


@dataclass
class PricingItem:
    service: str
    sku: str
    quantity: float
    hourly_price: float
    monthly_cost: float
    note: str
    savings_options: Optional[Any] = None


@dataclass
class PricingResult:
    items: List[PricingItem]
    total_monthly: float
    currency: str


@dataclass
class ProposalBundle:
    bom_text: str
    pricing_text: str
    proposal_text: str


@dataclass
class SessionData:
    thread: Any
    history: List[dict]
