import time
from decimal import Decimal

import httpx

_cache: dict[str, tuple[dict[str, float], float]] = {}
_CACHE_TTL = 3600  # 1 hour


async def get_exchange_rate(from_currency: str, to_currency: str) -> Decimal:
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return Decimal("1")

    now = time.time()
    cached = _cache.get(from_currency)
    if cached and now - cached[1] < _CACHE_TTL:
        rates = cached[0]
    else:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://open.er-api.com/v6/latest/{from_currency}")
            resp.raise_for_status()
            data = resp.json()
            rates = data["rates"]
            _cache[from_currency] = (rates, now)

    rate = rates.get(to_currency)
    if rate is None:
        raise ValueError(f"Unknown currency: {to_currency}")

    return Decimal(str(rate)).quantize(Decimal("0.000001"))
