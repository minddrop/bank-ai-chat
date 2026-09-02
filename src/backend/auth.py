"""
Authentication, Authorization & Step-Up MFA Module
Compliant with REQ-FUN-005, NIST SP 800-63B, Banking Act Article 13-2, and ADR-0014.
Provides zero-trust dual-tier access control: Level 1 (Inquiry) and Level 2 (Step-Up MFA).
"""

import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from typing import Dict, Any, Optional, Tuple

# Dynamic Secret Salt for JWT signing (In-VPC KMS CMK fallback)
JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "BANK_AI_KMS_CMK_HMAC_SECRET_KEY_AP_NORTHEAST_1_TOKYO"
).encode("utf-8")

JWT_TTL_SECONDS = 30 * 60  # 30 minutes TTL (REQ-FUN-005 §2)

# Regex patterns for High-Risk Transaction Intents (REQ-FUN-005 §3)
STEP_UP_PATTERNS = [
    # (regex, action_type, portal_path, description)
    (
        re.compile(r'(?:振込|送金|振替)(?:を|の)?(?:し(?:て|たい)|実行|手続き|頼む|お?願い)'),
        "FUND_TRANSFER",
        "transfer",
        "振込や送金などの資金移動"
    ),
    (
        re.compile(r'暗証番号(?:を|の)?(?:変更|リセット|変え|新しく)'),
        "PIN_CHANGE",
        "security/pin-change",
        "暗証番号の変更"
    ),
    (
        re.compile(r'(?:ログイン)?パスワード(?:を|の)?(?:変更|リセット|変え)'),
        "PASSWORD_CHANGE",
        "security/password",
        "ログインパスワード変更"
    ),
    (
        re.compile(r'定期預金(?:の|を)?(?:解約|払戻)'),
        "TIME_DEPOSIT_CANCEL",
        "deposit/cancel",
        "定期預金の解約・払戻"
    ),
    (
        re.compile(r'口座(?:の|を)?(?:解約|閉鎖)'),
        "ACCOUNT_CLOSURE",
        "account/close",
        "口座解約手続き"
    ),
    (
        re.compile(r'(?:振込)?限度額(?:の|を)?(?:変更|引き上げ|引き下げ|設定)'),
        "LIMIT_CHANGE",
        "settings/limit",
        "振込限度額の変更"
    ),
    (
        re.compile(r'キャッシュカード(?:の|を)?(?:再発行|再作成)'),
        "CARD_REISSUE",
        "card/reissue",
        "キャッシュカード再発行"
    ),
]

# In-memory Token Blacklist for revoked / logged-out tokens
TOKEN_BLACKLIST: set[str] = set()


def _base64url_encode(data: bytes) -> str:
    """Encode bytes to URL-safe base64 string without trailing '=' padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(s: str) -> bytes:
    """Decode URL-safe base64 string with optional padding."""
    rem = len(s) % 4
    if rem > 0:
        s += "=" * (4 - rem)
    return base64.urlsafe_b64decode(s.encode("utf-8"))


class AuthManager:
    """
    Manages JWT tokens, session lifecycle, revocation, and Step-Up MFA challenges.
    Grounded in REQ-FUN-005 and ADR-0014.
    """

    def __init__(self, secret_key: bytes = JWT_SECRET_KEY, ttl_seconds: int = JWT_TTL_SECONDS):
        self.secret_key = secret_key
        self.ttl_seconds = ttl_seconds

    def create_token(
        self,
        customer_id: str,
        tier: str = "STANDARD",
        auth_level: str = "LEVEL_1_INQUIRY",
        custom_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate RFC 7519 compliant JSON Web Token (HS256) for customer session.
        Payload claims: sub, tier, auth_level, exp, iat, jti.
        """
        header = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        jti = str(uuid.uuid4())

        payload = {
            "sub": customer_id,
            "tier": tier,
            "auth_level": auth_level,
            "iat": now,
            "exp": now + self.ttl_seconds,
            "jti": jti,
        }
        if custom_claims:
            payload.update(custom_claims)

        header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
        sig_b64 = _base64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token signature, expiration, and revocation status.
        Raises ValueError with specific RFC 7807 compatible error codes.
        """
        if not token:
            raise ValueError("AUTH_MISSING: Authentication token was not provided.")

        if token.startswith("Bearer "):
            token = token[7:].strip()

        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("AUTH_INVALID_FORMAT: Token structure is not valid JWT.")

        header_b64, payload_b64, sig_b64 = parts

        # Check signature
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
        expected_sig_b64 = _base64url_encode(expected_sig)

        if not hmac.compare_digest(sig_b64, expected_sig_b64):
            raise ValueError("AUTH_INVALID_SIGNATURE: Cryptographic token signature verification failed.")

        # Decode payload
        try:
            payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        except Exception as e:
            raise ValueError(f"AUTH_MALFORMED_PAYLOAD: Could not decode token payload: {e}")

        # Check token blacklist (revoked / logged out)
        jti = payload.get("jti")
        if jti and jti in TOKEN_BLACKLIST:
            raise ValueError("AUTH_REVOKED: Token has been revoked or logged out.")

        # Check expiration
        exp = payload.get("exp", 0)
        now = int(time.time())
        if now >= exp:
            raise ValueError(f"AUTH_EXPIRED: Token expired at {exp}, current time is {now}.")

        return payload

    def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding its jti to the blacklist."""
        try:
            payload = self.verify_token(token)
            jti = payload.get("jti")
            if jti:
                TOKEN_BLACKLIST.add(jti)
                return True
        except Exception:
            pass
        return False

    def detect_step_up_intent(self, message: str, session_id: str = "SESS-CURRENT") -> Optional[Dict[str, Any]]:
        """
        Detect if customer message attempts a Level 2 transaction (e.g. fund transfer, PIN reset).
        Returns Step-Up MFA Challenge payload (REQ-FUN-005 §3) or None if inquiry is safe.
        """
        cleaned = re.sub(r"\s+", "", message)
        for pattern, action_type, portal_path, desc in STEP_UP_PATTERNS:
            if pattern.search(cleaned):
                redirect_url = (
                    f"https://ib.megabank.co.jp/banking/{portal_path}?"
                    f"session_id={session_id}&auth_flow=mfa_step_up"
                )
                return {
                    "status": "STEP_UP_REQUIRED",
                    "action_type": action_type,
                    "target_action": desc,
                    "message": (
                        "振込や暗証番号の変更などのお取引・お手続きは、セキュリティ確保のため"
                        "インターネットバンキングの公式取引画面にて多要素認証（ワンタイムパスワード等）が必要です。"
                    ),
                    "redirect_url": redirect_url,
                    "required_auth_level": "MFA_HARDWARE_OR_BIOMETRIC"
                }
        return None


# Global singleton instance
auth_manager = AuthManager()
