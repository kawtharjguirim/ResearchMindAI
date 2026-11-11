"""
Jeton signé, de courte durée, pour la lecture d'une vidéo.

L'élément <video> ne peut pas envoyer d'en-tête Authorization : le lecteur demande donc un
lien signé (GET /sources/{id}/play-link, avec le Bearer habituel), puis charge la vidéo via
ce lien (GET /sources/{id}/file?token=...), vérifié sans Bearer.
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.core.config import Settings

PLAY_LINK_TTL = timedelta(minutes=10)


def _secret(settings: Settings) -> str:
    return settings.media_token_secret or settings.supabase_jwt_secret or "dev-insecure-media-token-secret"


def sign_play_token(source_id: str, user_id: str, settings: Settings) -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + PLAY_LINK_TTL
    payload = {"sid": source_id, "sub": user_id, "scope": "video_play", "exp": expires_at}
    return jwt.encode(payload, _secret(settings), algorithm="HS256"), expires_at


def verify_play_token(token: str, source_id: str, settings: Settings) -> str:
    """Renvoie l'id utilisateur si le jeton est valide pour cette source, sinon lève 401/403."""
    try:
        payload = jwt.decode(token, _secret(settings), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired play token") from exc
    if payload.get("scope") != "video_play" or payload.get("sid") != source_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token not valid for this source")
    return payload["sub"]
