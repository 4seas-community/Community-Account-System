from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_service
from ..schemas import CheckinClaimIn, CheckinTokenIn, CheckinTokenOut, NftClaimIn
from ..services import checkin_service

router = APIRouter(prefix="/v1/checkin", tags=["checkin"])


@router.post("/tokens", status_code=201, response_model=CheckinTokenOut)
def issue_token(
    body: CheckinTokenIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_service({"checkin:issue"})),
):
    token = checkin_service.issue(
        db, body.event_id, body.registration_id, body.event_url, body.ttl_seconds, body.max_uses
    )
    return CheckinTokenOut(token_id=token.id, claim_url=checkin_service.claim_url(token), expires_at=token.exp)


@router.post("/claim")
def claim(body: CheckinClaimIn, db: Session = Depends(get_db)):
    token = checkin_service.claim(db, body.token_id, body.sig)
    return {
        "valid": True,
        "event_id": token.event_id,
        "registration_id": token.registration_id,
        "claimed_at": token.claimed_at.isoformat() if token.claimed_at else None,
    }


@router.get("/tokens/{token_id}")
def get_token(
    token_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(require_service({"checkin:issue"})),
):
    token = checkin_service.get(db, token_id)
    return {
        "token_id": token.id,
        "event_id": token.event_id,
        "status": token.status,
        "uses": token.uses,
        "max_uses": token.max_uses,
        "expires_at": token.exp.isoformat(),
        "claimed_at": token.claimed_at.isoformat() if token.claimed_at else None,
        "nft_claim_id": token.nft_claim_id,
    }


@router.post("/tokens/{token_id}/nft-claim", status_code=201)
def nft_claim(
    token_id: str,
    body: NftClaimIn,
    db: Session = Depends(get_db),
    _: str = Depends(require_service({"checkin:issue"})),
):
    token = checkin_service.record_nft_claim(db, token_id, body.nft_contract, body.token_id, body.tx_hash)
    return {"token_id": token.id, "nft_claim_id": token.nft_claim_id}
