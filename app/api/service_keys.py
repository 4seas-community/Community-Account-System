import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import audit as audit_mod
from ..db import get_db
from ..deps import require_admin
from ..models import ServiceKey
from ..schemas import ServiceKeyIn
from ..security import hash_secret, new_id, new_opaque_token

router = APIRouter(prefix="/v1/service-keys", tags=["service-keys"])


@router.post("", status_code=201)
def create_key(body: ServiceKeyIn, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    secret = "cas_sk_" + new_opaque_token()
    key = ServiceKey(id=new_id(), name=body.name, key_hash=hash_secret(secret), scopes=json.dumps(body.scopes))
    db.add(key)
    db.flush()
    audit_mod.audit(db, "system", None, "service_key.create", {"name": body.name, "scopes": body.scopes})
    db.commit()
    return {"key_id": key.id, "secret": secret, "scopes": body.scopes}


@router.delete("/{key_id}", status_code=204)
def revoke_key(key_id: str, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    key = db.get(ServiceKey, key_id)
    if not key:
        from ..errors import NotFound

        raise NotFound("service key not found")
    from ..security import utcnow

    key.revoked_at = utcnow()
    audit_mod.audit(db, "system", None, "service_key.revoke", {"key_id": key_id})
    db.commit()
