from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Flight:
    flight_number: str
    departure: str
    arrival: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    currency: str
    airline: str
    available_seats: Optional[int] = None
