from dataclasses import dataclass


@dataclass
class Alert:
    crypto: str
    direction: str
    target_price: float

    def matches(self, price: float) -> bool:
        return (self.direction == "above" and price >= self.target_price) or (
            self.direction == "below" and price <= self.target_price
        )

    def __str__(self) -> str:
        return f"{self.crypto} {self.direction} €{self.target_price}"
