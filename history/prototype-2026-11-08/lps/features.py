import json
from pathlib import Path

REQUIRED = {"catalog", "orders", "payments"}
OPTIONAL = {"discount", "pix", "card"}


def validate(config):
    features = config.get("features", [])
    if not isinstance(features, list) or any(not isinstance(f, str) for f in features):
        raise ValueError("features deve ser uma lista de nomes")
    selected = set(features)
    if len(selected) != len(features):
        raise ValueError("Features duplicadas")
    if not REQUIRED <= selected:
        raise ValueError("Catálogo, pedidos e pagamentos são obrigatórios")
    if selected - REQUIRED - OPTIONAL:
        raise ValueError("Feature desconhecida")
    if not selected & {"pix", "card"}:
        raise ValueError("Selecione ao menos um meio de pagamento")
    if "discount" in selected and "pix" not in selected:
        raise ValueError("Desconto requer Pix")
    return config


def load(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))
