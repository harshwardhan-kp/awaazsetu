import hashlib, hmac, secrets, time
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from cryptography.fernet import Fernet
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

bearer = HTTPBearer(auto_error=False)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def contact_hash(channel, address):
    return hmac.new(
        settings.contact_hash_secret.encode(),
        f"{channel}:{address}".encode(),
        hashlib.sha256,
    ).hexdigest()


def encrypt(value):
    return (
        Fernet(settings.contact_encryption_key.encode())
        .encrypt(value.encode())
        .decode()
    )


def decrypt(value):
    return (
        Fernet(settings.contact_encryption_key.encode())
        .decrypt(value.encode())
        .decode()
    )


def make_token():
    return jwt.encode(
        {
            "sub": "coordinator",
            "exp": datetime.now(timezone.utc) + timedelta(hours=12),
            "iat": datetime.now(timezone.utc),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def admin(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    try:
        claims = jwt.decode(
            creds.credentials if creds else "",
            settings.jwt_secret,
            algorithms=["HS256"],
        )
        if claims.get("sub") != "coordinator":
            raise ValueError()
        return claims
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Coordinator login required")


buckets = defaultdict(deque)


def rate_limit(request: Request, category="intake", limit=30, seconds=60):
    # Do not trust arbitrary forwarding headers. Edge/proxy limits supplement this per-process guard.
    key = (request.client.host if request.client else "local", category)
    t = time.monotonic()
    q = buckets[key]
    while q and q[0] < t - seconds:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(
            429,
            "Too many requests; please try again shortly",
            headers={"Retry-After": str(seconds)},
        )
    q.append(t)
    if len(buckets) > 10000:
        for old in list(buckets):
            if not buckets[old] or buckets[old][-1] < t - 3600:
                buckets.pop(old, None)
