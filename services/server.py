from contextlib import closing
"""Três processos HTTP independentes; apenas a biblioteca padrão do Python."""
import argparse
import json
import os
import sqlite3
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lps.components import payment, pricing
from lps.features import load

PRODUCTS = [
    {"id": "1", "name": "Camiseta", "price_cents": 8990},
    {"id": "2", "name": "Jaqueta", "price_cents": 12990},
]


def remote(url, payload=None):
    request = Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 400:
            raise ValueError("Requisição recusada pelo serviço dependente") from exc
        raise ConnectionError("Serviço dependente falhou") from exc
    except (URLError, TimeoutError) as exc:
        raise ConnectionError("Serviço dependente indisponível") from exc


def make_handler(service, config, database, catalog_url, payments_url):
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                return self.respond(200, {"service": service, "product": config["name"], "features": config["features"]})
            if service == "catalog" and self.path == "/products":
                return self.respond(200, PRODUCTS)
            if service == "orders" and self.path.startswith("/orders/"):
                with closing(sqlite3.connect(database)) as db, db:
                    row = db.execute("SELECT payload FROM orders WHERE id = ?", (self.path.removeprefix("/orders/"),)).fetchone()
                return self.respond(200, json.loads(row[0])) if row else self.respond(404, {"error": "Pedido não encontrado"})
            self.respond(404, {"error": "Rota não encontrada"})

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("Corpo ausente ou muito grande")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Esperado objeto JSON")
                if service == "payments" and self.path == "/payments":
                    amount = body.get("amount_cents")
                    if type(amount) is not int or amount <= 0:
                        raise ValueError("Valor deve ser inteiro positivo em centavos")
                    return self.respond(200, payment(body.get("method"), config["features"]).authorize(amount))
                if service == "orders" and self.path == "/orders":
                    method = body.get("payment_method")
                    payment(method, config["features"])
                    quantity = body.get("quantity")
                    if type(quantity) is not int or not 1 <= quantity <= 100:
                        raise ValueError("Quantidade deve estar entre 1 e 100")
                    products = remote(catalog_url + "/products")
                    product = next((p for p in products if p["id"] == body.get("product_id")), None)
                    if product is None:
                        raise ValueError("Produto inexistente")
                    subtotal = product["price_cents"] * quantity
                    total = pricing(config["features"]).total(subtotal, method)
                    authorization = remote(payments_url + "/payments", {"method": method, "amount_cents": total})
                    order = {"id": str(uuid.uuid4()), "product_id": product["id"], "quantity": quantity,
                             "subtotal_cents": subtotal, "total_cents": total, "payment": authorization}
                    with closing(sqlite3.connect(database)) as db, db:
                        db.execute("INSERT INTO orders VALUES (?, ?)", (order["id"], json.dumps(order)))
                    return self.respond(201, order)
                self.respond(404, {"error": "Rota não encontrada"})
            except (ValueError, TypeError):
                self.respond(400, {"error": "Dados inválidos ou feature indisponível"})
            except ConnectionError:
                self.respond(503, {"error": "Dependência indisponível"})
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["catalog", "orders", "payments"])
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--config", default=os.getenv("PRODUCT_CONFIG", "configurations/basic.json"))
    args = parser.parse_args()
    config = load(args.config)
    database = os.getenv("ORDERS_DB", "orders.db")
    if args.service == "orders":
        with closing(sqlite3.connect(database)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
    handler = make_handler(args.service, config, database,
                           os.getenv("CATALOG_URL", "http://localhost:8001"),
                           os.getenv("PAYMENTS_URL", "http://localhost:8003"))
    ThreadingHTTPServer(("0.0.0.0", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
