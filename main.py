import re

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

SOURCE_URL = "https://test.ooobs.ru/api/orders"


def normalize_phone(raw) -> str | None:
    if not raw:
        return None
    digits = re.sub(r'\D', '', str(raw))
    if len(digits) == 11:
        if digits[0] == '8':
            digits = '7' + digits[1:]
        if digits[0] == '7':
            return '+' + digits
    elif len(digits) == 10:
        return '+7' + digits
    return None


@app.head("/")
async def ping_check():
    return {"status": "ok"}

@app.get("/")
async def sync():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(SOURCE_URL)
        data = resp.json()

    received = len(data)
    invalid_dropped = 0
    valid = []

    for item in data:
        phone = normalize_phone(item.get("phone", ""))
        if phone is None:
            invalid_dropped += 1
            continue
        valid.append({
            "name": item.get("name", ""),
            "phone": phone,
            "email": item.get("email", ""),
            "amount": item.get("amount", 0),
            "created_at": item.get("created_at", ""),
        })

    best: dict[str, dict] = {}
    for item in valid:
        p = item["phone"]
        if p not in best:
            best[p] = item
        else:
            ex = best[p]
            if item["amount"] > ex["amount"]:
                best[p] = item
            elif item["amount"] == ex["amount"] and item["created_at"] > ex["created_at"]:
                best[p] = item

    duplicates_merged = len(valid) - len(best)
    unique = len(best)

    clients = [
        {"name": v["name"], "phone": v["phone"], "email": v["email"], "amount": v["amount"]}
        for v in best.values()
    ]

    return JSONResponse({
        "clients": clients,
        "stats": {
            "received": received,
            "unique": unique,
            "duplicates_merged": duplicates_merged,
            "invalid_dropped": invalid_dropped,
        }
    })
