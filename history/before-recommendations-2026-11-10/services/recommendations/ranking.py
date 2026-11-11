"""Pure deterministic ranking. No network, persistence, user identity or AI."""
from collections import Counter
from services.recommendations.models import RecommendationItem, RecommendationResponse
from domain.models import ProductSummary


def rank(catalog, preferences, events, limit=6):
    by_id = {product.id: product for product in catalog.items}
    history = Counter()
    viewed = set()
    if preferences.use_history:
        for event in events:
            product = by_id.get(event['product_id'])
            if product:
                history[product.category] += 2 if event['kind'] == 'add_to_cart' else 1
                viewed.add(product.id)
    categories = {c.casefold() for c in preferences.categories}
    colors = {c.casefold() for c in preferences.colors}
    sizes = {s.casefold() for s in preferences.sizes}
    candidates = []
    for product in catalog.items:
        combinations = getattr(product, 'combinations', None)
        enabled = [c for c in combinations if c.enabled] if combinations is not None else []
        if combinations is not None and not enabled: continue
        if preferences.max_price_cents is not None and product.price_cents > preferences.max_price_cents: continue
        score, reasons = 0, []
        if product.category.casefold() in categories:
            score += 6; reasons.append('Da categoria que você escolheu')
        # A size/color preference must match ONE enabled combination, not a Cartesian product.
        matching = [c for c in enabled if (not sizes or c.size.casefold() in sizes) and (not colors or c.color.casefold() in colors)]
        if matching and (colors or sizes):
            score += (3 if colors else 0) + (2 if sizes else 0)
            reasons.append('Combinação habilitada nas suas preferências')
        if history[product.category]:
            score += min(history[product.category], 6)
            reasons.append('Relacionada às categorias do seu histórico')
        if product.id in viewed: score -= 2  # Prefer discovery among equally related pieces.
        if not reasons: reasons.append('Uma opção para conhecer a coleção')
        candidates.append((score, product.id, product, reasons[:3]))
    candidates.sort(key=lambda row: (-row[0], row[1]))
    items = tuple(RecommendationItem(**ProductSummary.model_validate({key:getattr(p,key) for key in ProductSummary.model_fields}).model_dump(), reasons=tuple(reasons)) for _, _, p, reasons in candidates[:limit])
    personalized = bool(categories or colors or sizes or preferences.max_price_cents is not None or history)
    return RecommendationResponse(store_id=catalog.store_id, catalog_revision=catalog.catalog_revision,
                                  mode='personalized' if personalized else 'discovery', items=items)
