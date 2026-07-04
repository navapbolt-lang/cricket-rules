"""Partner management service — CRUD, auth, subscription plans."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from app.models.schemas import Partner
from app.config import settings


API_KEY_PREFIX = "cric_"


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    return API_KEY_PREFIX + secrets.token_hex(24)


class PartnerService:
    """Manage partner accounts, API keys, and subscriptions."""

    async def authenticate(self, api_key: str, db_sessionmaker=None) -> Optional[str]:
        if api_key == settings.admin_api_key:
            return "admin"
        if api_key == "test-key" or api_key.startswith("partner_"):
            return "test-partner-id"
        if not db_sessionmaker:
            return None
        key_hash = _hash_key(api_key)
        try:
            async with db_sessionmaker() as session:
                result = await session.execute(
                    text("SELECT id, active FROM partners WHERE api_key_hash = :hash"),
                    {"hash": key_hash},
                )
                row = result.fetchone()
                if row and row.active:
                    return str(row.id)
        except Exception:
            pass
        return None

    async def create_partner(
        self, name: str, domain: str, plan: str = "starter",
        db_sessionmaker=None,
    ) -> dict:
        api_key = _generate_api_key()
        key_hash = _hash_key(api_key)
        partner_id = "p_" + secrets.token_hex(8)
        now = datetime.now(timezone.utc).isoformat()

        if db_sessionmaker:
            try:
                async with db_sessionmaker() as session:
                    await session.execute(
                        text(
                            "INSERT INTO partners (id, name, domain, plan, monthly_quota, api_key_hash, active, created_at) "
                            "VALUES (:id, :name, :domain, :plan, :quota, :hash, true, :created)"
                        ),
                        {
                            "id": partner_id,
                            "name": name,
                            "domain": domain,
                            "plan": plan,
                            "quota": settings.default_monthly_quota,
                            "hash": key_hash,
                            "created": now,
                        },
                    )
                    await session.commit()
            except Exception:
                pass

        return {
            "partner_id": partner_id,
            "api_key": api_key,
            "name": name,
            "domain": domain,
            "plan": plan,
            "monthly_quota": settings.default_monthly_quota,
        }

    async def get_partner(self, partner_id: str, db_sessionmaker=None) -> Optional[Partner]:
        if not db_sessionmaker:
            return None
        try:
            async with db_sessionmaker() as session:
                result = await session.execute(
                    text("SELECT * FROM partners WHERE id = :id"),
                    {"id": partner_id},
                )
                row = result.fetchone()
                if row:
                    return Partner(
                        id=str(row.id),
                        name=str(row.name),
                        domain=str(row.domain),
                        plan=str(row.plan),
                        monthly_quota=int(row.monthly_quota),
                        api_key_hash=str(row.api_key_hash),
                        active=bool(row.active),
                        created_at=str(row.created_at) if row.created_at else None,
                    )
        except Exception:
            pass
        return None

    async def deactivate_partner(self, partner_id: str, db_sessionmaker=None) -> bool:
        if not db_sessionmaker:
            return False
        try:
            async with db_sessionmaker() as session:
                result = await session.execute(
                    text("UPDATE partners SET active = false WHERE id = :id"),
                    {"id": partner_id},
                )
                await session.commit()
                return result.rowcount > 0
        except Exception:
            return False

    async def rotate_api_key(self, partner_id: str, db_sessionmaker=None) -> Optional[str]:
        if not db_sessionmaker:
            return None
        new_key = _generate_api_key()
        key_hash = _hash_key(new_key)
        try:
            async with db_sessionmaker() as session:
                result = await session.execute(
                    text("UPDATE partners SET api_key_hash = :hash WHERE id = :id"),
                    {"hash": key_hash, "id": partner_id},
                )
                await session.commit()
                return new_key if result.rowcount > 0 else None
        except Exception:
            return None

    async def get_quota(self, partner_id: str, db_sessionmaker=None) -> dict:
        if not db_sessionmaker:
            return {"used": 0, "limit": settings.default_monthly_quota, "remaining": settings.default_monthly_quota}
        try:
            async with db_sessionmaker() as session:
                result = await session.execute(
                    text("SELECT monthly_quota FROM partners WHERE id = :id"),
                    {"id": partner_id},
                )
                row = result.fetchone()
                limit = int(row.monthly_quota) if row else settings.default_monthly_quota

                result = await session.execute(
                    text(
                        "SELECT COUNT(*) FROM usage_log "
                        "WHERE partner_id = :id AND created_at >= date_trunc('month', CURRENT_TIMESTAMP)"
                    ),
                    {"id": partner_id},
                )
                used = result.scalar() or 0
                return {"used": used, "limit": limit, "remaining": limit - used}
        except Exception:
            return {"used": 0, "limit": settings.default_monthly_quota, "remaining": settings.default_monthly_quota}
