"""
Core Banking API Client Module
Used by the AI Chatbot and external services to communicate with the Core Banking System.
"""

from typing import Dict, Any, Optional
from core_banking.service import CoreBankingService


class CoreBankingClient:
    """
    Decoupled client wrapper providing standard extraction APIs for the AI Chat System.
    Can operate via direct service invocation or HTTP endpoint fallback.
    """

    def __init__(self, service: Optional[CoreBankingService] = None):
        self.service = service or CoreBankingService()

    def get_customer_summary(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch customer profile, balances, and recent transaction history."""
        return self.service.get_customer_profile(customer_id)

    def extract_account_info(self, customer_id: str) -> Dict[str, Any]:
        """Extract structured account info for AI context assembly."""
        return self.service.extract_account_info_for_ai(customer_id)
