from datetime import datetime
from typing import List
from api.models.flight import Flight

class ScootScraper:
    async def search_flights(self, from_airport: str, to_airport: str, date: datetime) -> List[Flight]:
        raise NotImplementedError("Tiger Airways search endpoint - Not implemented")
