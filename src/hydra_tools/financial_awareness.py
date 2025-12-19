"""
Financial Awareness for Hydra

Framework for financial data integration:
- Plaid banking integration (requires API keys)
- Cryptocurrency portfolio tracking
- Spending pattern analysis
- Budget alerts and insights
- Morning briefing integration

Author: Hydra Autonomous System
Phase: 14 - Financial Awareness (Week 23)
Created: 2025-12-18

Note: This module requires external API keys to be fully functional:
- PLAID_CLIENT_ID, PLAID_SECRET for banking
- Crypto API keys (optional) for portfolio tracking
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = Path(os.getenv("HYDRA_DATA_DIR", "/data"))
FINANCIAL_DIR = DATA_DIR / "financial"
FINANCIAL_DIR.mkdir(parents=True, exist_ok=True)

# Plaid configuration
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID", "")
PLAID_SECRET = os.getenv("PLAID_SECRET", "")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")  # sandbox, development, production

PLAID_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}

# Crypto APIs (optional)
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY", "")
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"  # Free, no key required

# Data files
ACCOUNTS_FILE = FINANCIAL_DIR / "accounts.json"
BUDGETS_FILE = FINANCIAL_DIR / "budgets.json"
CRYPTO_HOLDINGS_FILE = FINANCIAL_DIR / "crypto_holdings.json"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class BankAccount:
    """A linked bank account."""
    id: str
    name: str
    type: str  # checking, savings, credit, etc.
    institution: str
    balance: float
    available: Optional[float]
    last_updated: datetime
    plaid_item_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "institution": self.institution,
            "balance": self.balance,
            "available": self.available,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class Transaction:
    """A financial transaction."""
    id: str
    account_id: str
    date: datetime
    description: str
    amount: float
    category: List[str]
    pending: bool
    merchant: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "account_id": self.account_id,
            "date": self.date.isoformat(),
            "description": self.description,
            "amount": self.amount,
            "category": self.category,
            "pending": self.pending,
            "merchant": self.merchant,
        }


@dataclass
class CryptoHolding:
    """A cryptocurrency holding."""
    symbol: str
    name: str
    amount: float
    value_usd: float
    price_usd: float
    change_24h: float
    last_updated: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "amount": self.amount,
            "value_usd": self.value_usd,
            "price_usd": self.price_usd,
            "change_24h": self.change_24h,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class Budget:
    """A spending budget."""
    id: str
    name: str
    category: str
    amount: float
    period: str  # monthly, weekly
    spent: float
    remaining: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "amount": self.amount,
            "period": self.period,
            "spent": self.spent,
            "remaining": self.remaining,
            "percent_used": round((self.spent / self.amount) * 100, 1) if self.amount > 0 else 0,
        }


@dataclass
class FinancialSummary:
    """Overall financial summary."""
    total_bank_balance: float
    total_crypto_value: float
    net_worth: float
    monthly_spending: float
    monthly_income: float
    budget_status: Dict[str, float]  # category -> percent used
    accounts_count: int
    crypto_count: int
    alerts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_bank_balance": self.total_bank_balance,
            "total_crypto_value": self.total_crypto_value,
            "net_worth": self.net_worth,
            "monthly_spending": self.monthly_spending,
            "monthly_income": self.monthly_income,
            "budget_status": self.budget_status,
            "accounts_count": self.accounts_count,
            "crypto_count": self.crypto_count,
            "alerts": self.alerts,
        }


# =============================================================================
# Financial Manager
# =============================================================================

class FinancialManager:
    """Manages financial data and integrations."""

    def __init__(self):
        self.accounts: Dict[str, BankAccount] = {}
        self.crypto_holdings: Dict[str, CryptoHolding] = {}
        self.budgets: Dict[str, Budget] = {}
        self._load_state()

    def _load_state(self):
        """Load persisted state."""
        # Load accounts
        if ACCOUNTS_FILE.exists():
            try:
                data = json.loads(ACCOUNTS_FILE.read_text())
                for acc_data in data.get("accounts", []):
                    acc = BankAccount(
                        id=acc_data["id"],
                        name=acc_data["name"],
                        type=acc_data["type"],
                        institution=acc_data["institution"],
                        balance=acc_data["balance"],
                        available=acc_data.get("available"),
                        last_updated=datetime.fromisoformat(acc_data["last_updated"]),
                        plaid_item_id=acc_data.get("plaid_item_id"),
                    )
                    self.accounts[acc.id] = acc
            except Exception as e:
                logger.warning(f"Failed to load accounts: {e}")

        # Load crypto holdings
        if CRYPTO_HOLDINGS_FILE.exists():
            try:
                data = json.loads(CRYPTO_HOLDINGS_FILE.read_text())
                for holding_data in data.get("holdings", []):
                    holding = CryptoHolding(
                        symbol=holding_data["symbol"],
                        name=holding_data["name"],
                        amount=holding_data["amount"],
                        value_usd=holding_data["value_usd"],
                        price_usd=holding_data["price_usd"],
                        change_24h=holding_data.get("change_24h", 0),
                        last_updated=datetime.fromisoformat(holding_data["last_updated"]),
                    )
                    self.crypto_holdings[holding.symbol] = holding
            except Exception as e:
                logger.warning(f"Failed to load crypto holdings: {e}")

        # Load budgets
        if BUDGETS_FILE.exists():
            try:
                data = json.loads(BUDGETS_FILE.read_text())
                for budget_data in data.get("budgets", []):
                    budget = Budget(
                        id=budget_data["id"],
                        name=budget_data["name"],
                        category=budget_data["category"],
                        amount=budget_data["amount"],
                        period=budget_data["period"],
                        spent=budget_data.get("spent", 0),
                        remaining=budget_data.get("remaining", budget_data["amount"]),
                    )
                    self.budgets[budget.id] = budget
            except Exception as e:
                logger.warning(f"Failed to load budgets: {e}")

    def _save_state(self):
        """Persist state to files."""
        try:
            ACCOUNTS_FILE.write_text(json.dumps({
                "accounts": [a.to_dict() for a in self.accounts.values()],
                "updated_at": datetime.utcnow().isoformat(),
            }, indent=2))

            CRYPTO_HOLDINGS_FILE.write_text(json.dumps({
                "holdings": [h.to_dict() for h in self.crypto_holdings.values()],
                "updated_at": datetime.utcnow().isoformat(),
            }, indent=2))

            BUDGETS_FILE.write_text(json.dumps({
                "budgets": [b.to_dict() for b in self.budgets.values()],
                "updated_at": datetime.utcnow().isoformat(),
            }, indent=2))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def is_plaid_configured(self) -> bool:
        """Check if Plaid credentials are configured."""
        return bool(PLAID_CLIENT_ID and PLAID_SECRET)

    async def _plaid_request(self, endpoint: str, data: Dict) -> Optional[Dict]:
        """Make authenticated Plaid API request."""
        if not self.is_plaid_configured():
            return None

        url = f"{PLAID_URLS[PLAID_ENV]}{endpoint}"
        payload = {
            "client_id": PLAID_CLIENT_ID,
            "secret": PLAID_SECRET,
            **data,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Plaid API error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Plaid request failed: {e}")

        return None

    async def create_plaid_link_token(self, user_id: str = "hydra_user") -> Optional[str]:
        """Create a Plaid Link token for account connection."""
        result = await self._plaid_request("/link/token/create", {
            "user": {"client_user_id": user_id},
            "client_name": "Hydra Financial",
            "products": ["transactions"],
            "country_codes": ["US"],
            "language": "en",
        })

        if result:
            return result.get("link_token")
        return None

    async def exchange_public_token(self, public_token: str) -> Optional[str]:
        """Exchange public token from Link for access token."""
        result = await self._plaid_request("/item/public_token/exchange", {
            "public_token": public_token,
        })

        if result:
            return result.get("access_token")
        return None

    async def fetch_accounts(self, access_token: str) -> List[BankAccount]:
        """Fetch accounts for a Plaid item."""
        result = await self._plaid_request("/accounts/get", {
            "access_token": access_token,
        })

        if not result:
            return []

        accounts = []
        item = result.get("item", {})
        institution_id = item.get("institution_id", "unknown")

        for acc in result.get("accounts", []):
            balance = acc.get("balances", {})
            account = BankAccount(
                id=acc["account_id"],
                name=acc.get("name", "Unknown"),
                type=acc.get("type", "unknown"),
                institution=institution_id,
                balance=balance.get("current", 0),
                available=balance.get("available"),
                last_updated=datetime.utcnow(),
                plaid_item_id=item.get("item_id"),
            )
            accounts.append(account)
            self.accounts[account.id] = account

        self._save_state()
        return accounts

    async def fetch_crypto_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict]:
        """Fetch cryptocurrency prices from CoinGecko (free API)."""
        if not symbols and not self.crypto_holdings:
            return {}

        symbols = symbols or list(self.crypto_holdings.keys())

        try:
            async with httpx.AsyncClient() as client:
                # CoinGecko uses IDs, not symbols, so we need to map
                ids = ",".join(s.lower() for s in symbols)
                response = await client.get(
                    f"{COINGECKO_API_URL}/simple/price",
                    params={
                        "ids": ids,
                        "vs_currencies": "usd",
                        "include_24hr_change": "true",
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch crypto prices: {e}")

        return {}

    async def update_crypto_holdings(self) -> List[CryptoHolding]:
        """Update cryptocurrency holding values."""
        if not self.crypto_holdings:
            return []

        prices = await self.fetch_crypto_prices()
        now = datetime.utcnow()

        for symbol, holding in self.crypto_holdings.items():
            symbol_lower = symbol.lower()
            if symbol_lower in prices:
                price_data = prices[symbol_lower]
                holding.price_usd = price_data.get("usd", 0)
                holding.value_usd = holding.amount * holding.price_usd
                holding.change_24h = price_data.get("usd_24h_change", 0)
                holding.last_updated = now

        self._save_state()
        return list(self.crypto_holdings.values())

    def add_crypto_holding(self, symbol: str, name: str, amount: float) -> CryptoHolding:
        """Manually add a crypto holding."""
        holding = CryptoHolding(
            symbol=symbol.upper(),
            name=name,
            amount=amount,
            value_usd=0,
            price_usd=0,
            change_24h=0,
            last_updated=datetime.utcnow(),
        )
        self.crypto_holdings[holding.symbol] = holding
        self._save_state()
        return holding

    def remove_crypto_holding(self, symbol: str) -> bool:
        """Remove a crypto holding."""
        if symbol.upper() in self.crypto_holdings:
            del self.crypto_holdings[symbol.upper()]
            self._save_state()
            return True
        return False

    def add_budget(
        self,
        name: str,
        category: str,
        amount: float,
        period: str = "monthly"
    ) -> Budget:
        """Add a spending budget."""
        budget_id = f"budget_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        budget = Budget(
            id=budget_id,
            name=name,
            category=category,
            amount=amount,
            period=period,
            spent=0,
            remaining=amount,
        )
        self.budgets[budget.id] = budget
        self._save_state()
        return budget

    def update_budget_spending(self, budget_id: str, spent: float) -> Optional[Budget]:
        """Update budget spending."""
        if budget_id in self.budgets:
            budget = self.budgets[budget_id]
            budget.spent = spent
            budget.remaining = budget.amount - spent
            self._save_state()
            return budget
        return None

    def get_summary(self) -> FinancialSummary:
        """Get overall financial summary."""
        total_bank = sum(a.balance for a in self.accounts.values())
        total_crypto = sum(h.value_usd for h in self.crypto_holdings.values())

        # Generate alerts
        alerts = []
        for budget in self.budgets.values():
            percent_used = (budget.spent / budget.amount * 100) if budget.amount > 0 else 0
            if percent_used >= 90:
                alerts.append(f"Budget '{budget.name}' is {percent_used:.0f}% used")
            elif percent_used >= 75:
                alerts.append(f"Budget '{budget.name}' is {percent_used:.0f}% used (warning)")

        budget_status = {
            b.category: (b.spent / b.amount * 100) if b.amount > 0 else 0
            for b in self.budgets.values()
        }

        return FinancialSummary(
            total_bank_balance=total_bank,
            total_crypto_value=total_crypto,
            net_worth=total_bank + total_crypto,
            monthly_spending=0,  # Would need transaction data
            monthly_income=0,  # Would need transaction data
            budget_status=budget_status,
            accounts_count=len(self.accounts),
            crypto_count=len(self.crypto_holdings),
            alerts=alerts,
        )

    async def get_morning_briefing_data(self) -> Dict[str, Any]:
        """Get financial data formatted for morning briefing."""
        summary = self.get_summary()

        # Update crypto prices if we have holdings
        if self.crypto_holdings:
            await self.update_crypto_holdings()

        return {
            "configured": self.is_plaid_configured() or bool(self.accounts) or bool(self.crypto_holdings),
            "net_worth": summary.net_worth,
            "bank_balance": summary.total_bank_balance,
            "crypto_value": summary.total_crypto_value,
            "accounts_linked": summary.accounts_count,
            "crypto_holdings": len(self.crypto_holdings),
            "budget_alerts": [a for a in summary.alerts if "Budget" in a],
            "top_movers": [
                {
                    "symbol": h.symbol,
                    "change": h.change_24h,
                    "value": h.value_usd,
                }
                for h in sorted(
                    self.crypto_holdings.values(),
                    key=lambda x: abs(x.change_24h),
                    reverse=True
                )[:3]
            ] if self.crypto_holdings else [],
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_financial_manager: Optional[FinancialManager] = None


def get_financial_manager() -> FinancialManager:
    """Get or create financial manager singleton."""
    global _financial_manager
    if _financial_manager is None:
        _financial_manager = FinancialManager()
    return _financial_manager


# =============================================================================
# Pydantic Models
# =============================================================================

class CryptoHoldingRequest(BaseModel):
    symbol: str
    name: str
    amount: float


class BudgetRequest(BaseModel):
    name: str
    category: str
    amount: float
    period: str = "monthly"


class BudgetUpdateRequest(BaseModel):
    spent: float


class PlaidPublicTokenRequest(BaseModel):
    public_token: str


# =============================================================================
# FastAPI Router
# =============================================================================

def create_financial_router() -> APIRouter:
    """Create financial awareness API router."""
    router = APIRouter(prefix="/financial", tags=["financial"])

    @router.get("/status")
    async def get_status():
        """Get financial integration status."""
        manager = get_financial_manager()
        return {
            "plaid_configured": manager.is_plaid_configured(),
            "plaid_env": PLAID_ENV,
            "accounts_linked": len(manager.accounts),
            "crypto_holdings": len(manager.crypto_holdings),
            "budgets_configured": len(manager.budgets),
            "features_available": {
                "banking": manager.is_plaid_configured(),
                "crypto": True,  # CoinGecko is free
                "budgets": True,
            },
        }

    @router.get("/summary")
    async def get_summary():
        """Get financial summary."""
        manager = get_financial_manager()
        return manager.get_summary().to_dict()

    @router.get("/accounts")
    async def get_accounts():
        """Get linked bank accounts."""
        manager = get_financial_manager()
        return {
            "count": len(manager.accounts),
            "accounts": [a.to_dict() for a in manager.accounts.values()],
        }

    # Plaid integration endpoints
    @router.post("/plaid/link-token")
    async def create_link_token():
        """Create Plaid Link token for account connection."""
        manager = get_financial_manager()
        if not manager.is_plaid_configured():
            raise HTTPException(
                status_code=400,
                detail="Plaid not configured. Set PLAID_CLIENT_ID and PLAID_SECRET.",
            )

        token = await manager.create_plaid_link_token()
        if token:
            return {"link_token": token}
        raise HTTPException(status_code=500, detail="Failed to create link token")

    @router.post("/plaid/exchange")
    async def exchange_token(request: PlaidPublicTokenRequest):
        """Exchange Plaid public token for access token and fetch accounts."""
        manager = get_financial_manager()
        if not manager.is_plaid_configured():
            raise HTTPException(status_code=400, detail="Plaid not configured")

        access_token = await manager.exchange_public_token(request.public_token)
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to exchange token")

        accounts = await manager.fetch_accounts(access_token)
        return {
            "success": True,
            "accounts_linked": len(accounts),
            "accounts": [a.to_dict() for a in accounts],
        }

    # Crypto endpoints
    @router.get("/crypto")
    async def get_crypto_holdings():
        """Get cryptocurrency holdings."""
        manager = get_financial_manager()
        holdings = await manager.update_crypto_holdings()
        return {
            "count": len(holdings),
            "total_value_usd": sum(h.value_usd for h in holdings),
            "holdings": [h.to_dict() for h in holdings],
        }

    @router.post("/crypto")
    async def add_crypto_holding(request: CryptoHoldingRequest):
        """Add a cryptocurrency holding."""
        manager = get_financial_manager()
        holding = manager.add_crypto_holding(
            request.symbol,
            request.name,
            request.amount,
        )
        # Fetch current price
        await manager.update_crypto_holdings()
        return {
            "success": True,
            "holding": manager.crypto_holdings.get(request.symbol.upper()).to_dict(),
        }

    @router.delete("/crypto/{symbol}")
    async def remove_crypto_holding(symbol: str):
        """Remove a cryptocurrency holding."""
        manager = get_financial_manager()
        if manager.remove_crypto_holding(symbol):
            return {"success": True, "message": f"Removed {symbol}"}
        raise HTTPException(status_code=404, detail=f"Holding not found: {symbol}")

    @router.get("/crypto/prices")
    async def get_crypto_prices(symbols: str = Query(..., description="Comma-separated symbols")):
        """Get current prices for cryptocurrencies."""
        manager = get_financial_manager()
        symbol_list = [s.strip() for s in symbols.split(",")]
        prices = await manager.fetch_crypto_prices(symbol_list)
        return {"prices": prices}

    # Budget endpoints
    @router.get("/budgets")
    async def get_budgets():
        """Get configured budgets."""
        manager = get_financial_manager()
        return {
            "count": len(manager.budgets),
            "budgets": [b.to_dict() for b in manager.budgets.values()],
        }

    @router.post("/budgets")
    async def add_budget(request: BudgetRequest):
        """Add a spending budget."""
        manager = get_financial_manager()
        budget = manager.add_budget(
            request.name,
            request.category,
            request.amount,
            request.period,
        )
        return {"success": True, "budget": budget.to_dict()}

    @router.put("/budgets/{budget_id}")
    async def update_budget(budget_id: str, request: BudgetUpdateRequest):
        """Update budget spending."""
        manager = get_financial_manager()
        budget = manager.update_budget_spending(budget_id, request.spent)
        if budget:
            return {"success": True, "budget": budget.to_dict()}
        raise HTTPException(status_code=404, detail=f"Budget not found: {budget_id}")

    @router.delete("/budgets/{budget_id}")
    async def delete_budget(budget_id: str):
        """Delete a budget."""
        manager = get_financial_manager()
        if budget_id in manager.budgets:
            del manager.budgets[budget_id]
            manager._save_state()
            return {"success": True, "message": f"Deleted budget {budget_id}"}
        raise HTTPException(status_code=404, detail=f"Budget not found: {budget_id}")

    @router.get("/morning-briefing-data")
    async def get_morning_briefing_data():
        """Get financial data formatted for morning briefing."""
        manager = get_financial_manager()
        return await manager.get_morning_briefing_data()

    return router
