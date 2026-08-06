"""
LLM Client Factory Module - Japanese Major Bank AI Customer Assistant
Provides unified access to AWS Bedrock Nova Lite (production) and Local LLM Provider (development).
"""

import os
from typing import Union
from llm.bedrock_nova import BedrockNovaLiteClient
from llm.local_llm import LocalLLMClient

def get_llm_client() -> Union[BedrockNovaLiteClient, LocalLLMClient]:
    """
    Factory function returning the configured LLM client.
    Controlled via LLM_PROVIDER environment variable ('bedrock' or 'local').
    """
    provider = os.environ.get("LLM_PROVIDER", "bedrock").lower().strip()
    if provider == "local":
        return LocalLLMClient()
    return BedrockNovaLiteClient()
