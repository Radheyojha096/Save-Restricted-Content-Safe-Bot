import os
import json
import asyncio

STORAGE = os.path.join(os.path.dirname(__file__), "users_storage.json")

def _read():
    if not os.path.exists(STORAGE):
        return {"users": []}
    with open(STORAGE, "r") as f:
        return json.load(f)

def _write(data):
    with open(STORAGE, "w") as f:
        json.dump(data, f)

async def get_users():
    data = await asyncio.to_thread(_read)
    return data.get("users", [])

async def get_user(user):
    users = await get_users()
    return user in users

async def add_user(user):
    data = await asyncio.to_thread(_read)
    users = data.get("users", [])
    if user in users:
        return
    users.append(user)
    data["users"] = users
    await asyncio.to_thread(_write, data)

async def del_user(user):
    data = await asyncio.to_thread(_read)
    users = data.get("users", [])
    if user in users:
        users.remove(user)
        data["users"] = users
        await asyncio.to_thread(_write, data)




