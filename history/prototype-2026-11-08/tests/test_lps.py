from contextlib import closing
import json
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from lps.features import load, validate
from services.server import make_handler


class ProductLineTests(unittest.TestCase):
    def test_constraints(self):
        for features in [[], ["catalog", "orders", "payments"],
                         ["catalog", "orders", "payments", "card", "discount"],
                         ["catalog", "orders", "payments", "pix", "unknown"]]:
            with self.subTest(features=features), self.assertRaises(ValueError):
                validate({"features": features})

    def test_products_over_http(self):
        for variant, total in [("basic", 8990), ("premium", 8541)]:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                config = load(f"configurations/{variant}.json")
                database = str(Path(tmp) / "orders.db")
                with closing(sqlite3.connect(database)) as db, db:
                    db.execute("CREATE TABLE orders (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                servers = []
                try:
                    def start(service, catalog="", payments=""):
                        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service, config, database, catalog, payments))
                        servers.append(server)
                        threading.Thread(target=server.serve_forever, daemon=True).start()
                        return f"http://127.0.0.1:{server.server_port}"
                    catalog = start("catalog")
                    payments = start("payments")
                    orders = start("orders", catalog, payments)
                    def buy(method, quantity=1):
                        request = Request(orders + "/orders", data=json.dumps({"product_id": "1", "quantity": quantity, "payment_method": method}).encode(), headers={"Content-Type": "application/json"})
                        with urlopen(request) as response:
                            self.assertEqual(response.status, 201)
                            return json.load(response)
                    order = buy("pix")
                    self.assertEqual(order["total_cents"], total)
                    with urlopen(orders + "/orders/" + order["id"]) as response:
                        self.assertEqual(json.load(response), order)
                    if variant == "basic":
                        with self.assertRaises(HTTPError) as error:
                            buy("card")
                        self.assertEqual(error.exception.code, 400)
                    else:
                        self.assertEqual(buy("card")["total_cents"], 8990)
                    with self.assertRaises(HTTPError) as error:
                        buy("pix", -1)
                    self.assertEqual(error.exception.code, 400)
                    servers[0].shutdown()
                    servers[0].server_close()
                    with self.assertRaises(HTTPError) as error:
                        buy("pix")
                    self.assertEqual(error.exception.code, 503)
                finally:
                    for server in servers:
                        server.shutdown()
                        server.server_close()


if __name__ == "__main__":
    unittest.main()
