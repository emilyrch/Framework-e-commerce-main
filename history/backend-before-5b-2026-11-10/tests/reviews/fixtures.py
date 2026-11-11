from datetime import datetime
from zoneinfo import ZoneInfo

NOW = datetime(2026, 11, 9, 8, 0, tzinfo=ZoneInfo('America/Sao_Paulo'))
OWNER = 'a' * 64


def review_body(variant):
    address = {'recipient': 'Cliente Fictício', 'street': 'Rua Exemplo', 'number': '10',
               'district': 'Centro', 'city': 'São Paulo', 'state': 'SP', 'postal_code': '01001000'}
    if variant == 'clothing':
        return {'store_id': 'roupas-demo', 'items': [
            {'product_id': 'camiseta', 'combination_id': 'camiseta-g-azul', 'quantity': 2},
            {'product_id': 'camiseta', 'combination_id': 'camiseta-m-preta', 'quantity': 1}],
            'delivery': {'address': address}, 'payment_method': 'simulated_pix'}
    return {'store_id': 'alimentos-demo', 'items': [{'product_id': 'granola', 'quantity': 1}, {'product_id': 'suco', 'quantity': 2}],
            'delivery': {'address': address, 'slot_id': 'food-windows-v1:2026-11-09:morning'}, 'payment_method': 'simulated_pix'}
