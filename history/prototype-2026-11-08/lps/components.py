from typing import Protocol


class Pricing(Protocol):
    def total(self, subtotal: int, method: str) -> int: ...


class RegularPrice:
    def total(self, subtotal: int, method: str) -> int:
        return subtotal


class PixDiscount:
    def total(self, subtotal: int, method: str) -> int:
        # Valores monetários em centavos; arredondamento inteiro.
        return (subtotal * 95 + 50) // 100 if method == "pix" else subtotal


class Payment(Protocol):
    def authorize(self, amount: int) -> dict: ...


class SimulatedPix:
    def authorize(self, amount: int) -> dict:
        return {"method": "pix", "status": "simulated_approved", "amount_cents": amount}


class SimulatedCard:
    def authorize(self, amount: int) -> dict:
        return {"method": "card", "status": "simulated_approved", "amount_cents": amount}


def pricing(features) -> Pricing:
    return PixDiscount() if "discount" in features else RegularPrice()


def payment(method, features) -> Payment:
    if method not in {"pix", "card"} or method not in features:
        raise ValueError("Meio de pagamento indisponível neste produto")
    return {"pix": SimulatedPix, "card": SimulatedCard}[method]()
