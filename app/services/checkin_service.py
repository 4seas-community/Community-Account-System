from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy.orm import Session

from .. import audit as audit_mod
from ..config import get_settings
from ..errors import Conflict, Gone, NotFound, Unauthorized
from ..models import CheckinToken
from ..security import new_id, sign_hmac, utcnow, verify_hmac

settings = get_settings()


def _signature(token_id: str, event_id: str, registration_id: str, exp: datetime) -> str:
    exp_ts = str(int(exp.timestamp()))
    return sign_hmac(token_id + "|" + event_id + "|" + registration_id + "|" + exp_ts)


def issue(db: Session, event_id: str, registration_id: str, event_url: str, ttl_seconds: int, max_uses: int) -> CheckinToken:
    token_id = new_id()
    exp = utcnow() + timedelta(seconds=ttl_seconds)
    sig = _signature(token_id, event_id, registration_id, exp)
    token = CheckinToken(
        id=token_id,
        event_id=event_id,
        registration_id=registration_id,
        event_url=event_url,
        sig=sig,
        exp=exp,
        max_uses=max_uses,
    )
    db.add(token)
    db.flush()
    audit_mod.audit(db, "service", None, "checkin.issue", {"token_id": token_id, "event_id": event_id})
    db.commit()
    db.refresh(token)
    return token


def claim_url(token: CheckinToken) -> str:
    sep = "&" if "?" in token.event_url else "?"
    return token.event_url + sep + "ck=" + token.id + "&sig=" + quote(token.sig)


def claim(db: Session, token_id: str, sig: str) -> CheckinToken:
    token = db.get(CheckinToken, token_id)
    if not token:
        raise NotFound("unknown token")
    if token.status == "expired" or token.exp < utcnow():
        token.status = "expired"
        db.commit()
        raise Gone("claim url expired")
    if not verify_hmac("|".join([token.id, token.event_id, token.registration_id, str(int(token.exp.timestamp()))]), sig):
        raise Unauthorized("bad signature")
    if token.uses >= token.max_uses:
        token.status = "claimed"
        db.commit()
        raise Conflict("already claimed")
    token.uses += 1
    if token.uses >= token.max_uses:
        token.status = "claimed"
    token.claimed_at = utcnow()
    audit_mod.audit(db, "system", None, "checkin.claim", {"token_id": token.id, "event_id": token.event_id})
    db.commit()
    db.refresh(token)
    return token


def get(db: Session, token_id: str) -> CheckinToken:
    token = db.get(CheckinToken, token_id)
    if not token:
        raise NotFound("unknown token")
    if token.status == "pending" and token.exp < utcnow():
        token.status = "expired"
        db.commit()
        db.refresh(token)
    return token


def record_nft_claim(db: Session, token_id: str, nft_contract: str, token_id_nft: str, tx_hash: str) -> CheckinToken:
    token = get(db, token_id)
    token.nft_claim_id = new_id()
    token.nft_contract = nft_contract
    token.nft_token_id = token_id_nft
    token.nft_tx_hash = tx_hash
    audit_mod.audit(db, "service", None, "checkin.nft_claim", {"token_id": token_id, "tx_hash": tx_hash})
    db.commit()
    db.refresh(token)
    return token
