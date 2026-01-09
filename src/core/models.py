"""Shared data models for orchestrator flows."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class BOMItem:
    serviceName: str
    sku: str
    quantity: float
    region: str
    armRegionName: str
    hours_per_month: float


@dataclass
class SavingsOption:
    """Savings option (reserved instance or savings plan)."""

    description: str
    estimated_monthly_savings: float


@dataclass
class PricingItem:
    """Pricing output item - matches PRD Section 4.3."""

    serviceName: str  # Service name from BOM
    sku: str  # SKU from BOM
    region: str  # Human-readable region from BOM
    armRegionName: str  # ARM region code from BOM
    quantity: float  # Quantity from BOM
    hours_per_month: float  # Operating hours from BOM
    unit_price: float  # Hourly rate from pricing API
    monthly_cost: float  # Monthly cost from pricing API
    notes: Optional[str] = None  # Optional notes


@dataclass
class PricingResult:
    """Pricing output - matches PRD Section 4.3."""

    items: List[PricingItem]
    total_monthly: float  # Sum of monthly_cost * quantity
    currency: str  # e.g., "USD"
    pricing_date: str  # ISO 8601 date, e.g., "2026-01-07"
    savings_options: Optional[List[SavingsOption]] = None  # Cost optimization suggestions
    errors: Optional[List[str]] = None  # Pricing lookup failures


@dataclass
class ProposalBundle:
    bom_text: str
    pricing_text: str
    proposal_text: str


@dataclass
class ProgressEvent:
    """Progress event for streaming workflow updates."""

    event_type: str  # "agent_start", "agent_progress", "workflow_complete", "error"
    agent_name: str  # "bom_agent", "pricing_agent", "proposal_agent", ""
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class SessionData:
    thread: Any
    history: List[dict]
    turn_count: int = 0  # Track conversation turns for 20-turn limit
    bom_items: List[Dict[str, Any]] = None  # Incremental BOM items built during conversation

    def __post_init__(self):
        """Initialize mutable default values."""
        if self.bom_items is None:
            self.bom_items = []
