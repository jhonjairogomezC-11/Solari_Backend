"""Rate limiting con slowapi (basado en la IP del cliente)."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# headers_enabled=False: evita que slowapi exija un parámetro `response` en cada
# endpoint. El rate limiting sigue activo; solo no se inyectan cabeceras X-RateLimit.
limiter = Limiter(key_func=get_remote_address, headers_enabled=False)
