from fastapi import Request, HTTPException
from jose import jwt, JWTError
import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64

JWKS_URL = "https://auth.yourdomain.com/.well-known/jwks.json"
ALGORITHM = "RS256"
AUDIENCE = "your-service"
ISSUER = "https://auth.yourdomain.com"

cached_keys = {}


async def get_signing_key(kid: str):
    if kid in cached_keys:
        return cached_keys[kid]

    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URL)
        jwks = response.json()

    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            # Convert JWK to PEM format
            n = base64.urlsafe_b64decode(key["n"] + "==")
            e = base64.urlsafe_b64decode(key["e"] + "==")

            public_key = rsa.RSAPublicNumbers(
                int.from_bytes(e, 'big'),
                int.from_bytes(n, 'big')
            ).public_key()

            pem_key = public_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            cached_keys[kid] = pem_key
            return pem_key

    raise Exception("Signing key not found")


class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)

        token = auth_header.split(" ")[1]
        try:
            headers = jwt.get_unverified_header(token)
            kid = headers["kid"]

            public_key = await get_signing_key(kid)

            payload = jwt.decode(
                token,
                public_key,
                algorithms=[ALGORITHM],
                audience=AUDIENCE,
                issuer=ISSUER,
            )

            request.state.userid = payload.get("sub")

        except (JWTError, Exception):
            raise HTTPException(status_code=401, detail="Invalid JWT token")

        return await call_next(request)
