"""Seed test partners into the database for development.

Usage: python scripts/seed_partners.py
"""

import asyncio
from app.services.partner_service import PartnerService


async def seed():
    svc = PartnerService()
    partners = [
        {"name": "Demo Partner", "domain": "demo.example.com", "plan": "starter"},
        {"name": "Internal Test", "domain": "internal.cricketrules.ai", "plan": "enterprise"},
        {"name": "Cricbuzz (Mock)", "domain": "cricbuzz.com", "plan": "enterprise"},
    ]
    for p in partners:
        result = await svc.create_partner(**p)
        print(f"  [{result['plan']}] {result['name']} <{result['domain']}>")
        print(f"    Partner ID: {result['partner_id']}")
        print(f"    API Key:    {result['api_key']}")
        print()


def seed_partners():
    print("Seeding partner accounts...")
    asyncio.run(seed())
    print("Done. Save the API keys above — they won't be shown again.")


if __name__ == "__main__":
    seed_partners()
