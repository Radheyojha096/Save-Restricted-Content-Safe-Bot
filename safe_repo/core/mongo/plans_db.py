import os
import json
import asyncio
from datetime import datetime, timezone

STORAGE = os.path.join(os.path.dirname(__file__), "plans_storage.json")

def _read():
    if not os.path.exists(STORAGE):
        return {}
    with open(STORAGE, "r") as f:
        return json.load(f)

def _write(data):
    with open(STORAGE, "w") as f:
        json.dump(data, f)

async def add_premium(user_id, expire_date):
    data = await asyncio.to_thread(_read)
    data[str(user_id)] = {"expire_date": expire_date.isoformat() if hasattr(expire_date, 'isoformat') else str(expire_date)}
    await asyncio.to_thread(_write, data)

async def remove_premium(user_id):
    data = await asyncio.to_thread(_read)
    data.pop(str(user_id), None)
    await asyncio.to_thread(_write, data)

from config import OWNER_ID

# List of users with lifetime premium access
PREMIUM_USERS = [7453797299, 8175151355, 8552899459]

async def premium_users():
    data = await asyncio.to_thread(_read)
    users = [int(k) for k in data.keys()]
    # Add owner and premium users to premium users list if not already present (lifetime premium)
    for owner_id in OWNER_ID:
        if owner_id not in users:
            users.append(owner_id)
    for premium_user in PREMIUM_USERS:
        if premium_user not in users:
            users.append(premium_user)
    return users

async def check_premium(user_id):
    data = await asyncio.to_thread(_read)
    entry = data.get(str(user_id))
    
    # Check if user is owner or in premium users list - if yes, return permanent premium
    if user_id in OWNER_ID or user_id in PREMIUM_USERS:
        return {"_id": user_id, "expire_date": None}  # None indicates lifetime premium
    
    if not entry:
        return None
    try:
        expire = datetime.fromisoformat(entry.get("expire_date")).replace(tzinfo=timezone.utc)
    except Exception:
        expire = None
    return {"_id": int(user_id), "expire_date": expire}

async def check_and_remove_expired_users():
    data = await asyncio.to_thread(_read)
    now = datetime.now(timezone.utc)
    removed = []
    for k, v in list(data.items()):
        try:
            expire = datetime.fromisoformat(v.get("expire_date")).replace(tzinfo=timezone.utc)
            if expire and expire < now:
                data.pop(k, None)
                removed.append(k)
        except Exception:
            continue
    if removed:
        await asyncio.to_thread(_write, data)
    for r in removed:
        print(f"Removed user {r} due to expired plan.")
