from fastapi import APIRouter, Depends

from app import schemas
from app.config import Settings, get_settings
from app.pipeline import rule_engine

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=schemas.RulePackOut)
def get_rule_pack(settings: Settings = Depends(get_settings)) -> schemas.RulePackOut:
    rule_pack = rule_engine.load_rule_pack(str(settings.rule_pack_path))
    return schemas.RulePackOut(
        rule_pack_version=rule_pack.version,
        effective_date=rule_pack.effective_date,
        sha256_hash=rule_pack.sha256_hash,
        scope="MVP: physical retail-package label declarations only.",
        fields=[
            schemas.RulePackFieldOut(
                field_id=f["field_id"], clause=f["clause"], title=f["title"], legal_reference=f["legal_reference"]
            )
            for f in rule_pack.fields
        ],
    )
