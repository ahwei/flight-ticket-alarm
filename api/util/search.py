from datetime import datetime
from typing import List, Optional
from amadeus import Client, ResponseError
from dotenv import load_dotenv

load_dotenv()


class FlightData:
    def __init__(self, date, from_airport, to_airport):
        self.date = date
        self.from_airport = from_airport
        self.to_airport = to_airport


class Passengers:
    def __init__(self, adults=1, children=0, infants_in_seat=0, infants_on_lap=0):
        self.adults = adults
        self.children = children
        self.infants_in_seat = infants_in_seat
        self.infants_on_lap = infants_on_lap


def search_flights(data, amadeus: Client):
    default_flight_data = [
        FlightData(
            date=datetime.now().strftime("%Y-%m-%d"),
            from_airport="TPE",
            to_airport="NRT",
        )
    ]

    flight_data_raw = data.get("flight_data", [])
    flight_data = (
        [
            FlightData(
                date=f.get("date"),
                from_airport=f.get("from_airport"),
                to_airport=f.get("to_airport"),
            )
            for f in flight_data_raw
        ]
        if flight_data_raw
        else default_flight_data
    )

    passengers_data = data.get("passengers", {})
    passengers = Passengers(
        adults=int(passengers_data.get("adults", 1)),
        children=int(passengers_data.get("children", 0)),
        infants_in_seat=int(passengers_data.get("infants_in_seat", 0)),
        infants_on_lap=int(passengers_data.get("infants_on_lap", 0)),
    )

    trip = data.get("trip", "one-way")
    seat = data.get("seat", "economy")

    seat_mapping = {
        "economy": "ECONOMY",
        "premium-economy": "PREMIUM_ECONOMY",
        "business": "BUSINESS",
        "first": "FIRST",
    }
    travel_class = seat_mapping.get(seat.lower(), "ECONOMY")

    departureDate = None
    returnDate = None

    if len(flight_data) >= 1:
        departureDate = flight_data[0].date

    if trip == "round-trip" and len(flight_data) >= 2:
        returnDate = flight_data[1].date
    elif trip == "round-trip" and len(flight_data) == 1:
        returnDate = data.get("return_date")
        if not returnDate:
            raise ValueError("Round-trip requires a return date")

    originLocationCode = flight_data[0].from_airport
    destinationLocationCode = flight_data[0].to_airport

    adults = passengers.adults
    children = passengers.children
    infants = passengers.infants_in_seat + passengers.infants_on_lap

    search_params = {
        "originLocationCode": originLocationCode,
        "destinationLocationCode": destinationLocationCode,
        "departureDate": departureDate,
        "adults": adults,
        "travelClass": travel_class,
        "currencyCode": "TWD",
        "nonStop": "true",
    }

    if returnDate:
        search_params["returnDate"] = returnDate

    if children > 0:
        search_params["children"] = children

    if infants > 0:
        search_params["infants"] = infants

    response = amadeus.shopping.flight_offers_search.get(**search_params)
    offers = response.data

    search_criteria = {
        "flight_data": [
            {
                "date": fd.date,
                "from_airport": fd.from_airport,
                "to_airport": fd.to_airport,
            }
            for fd in flight_data
        ],
        "trip": trip,
        "seat": seat,
        "passengers": passengers.__dict__,
    }

    return offers, search_criteria


def search_flights_simple(amadeus: Client):
    try:
        search_params = {
            "originLocationCode": "KHH",
            "destinationLocationCode": "NRT",
            "departureDate": "2024-12-13",
            "returnDate": "2024-12-16",
            "adults": 2,
            "travelClass": "ECONOMY",
            "currencyCode": "TWD",
            "max": 10,
            "nonStop": "true",
        }

        response = amadeus.shopping.flight_offers_search.get(**search_params)

        if not response.data:
            return []

        return response.data

    except ResponseError as error:
        error_msg = error.response.body if hasattr(error, "response") else str(error)
        raise ValueError(f"航班搜尋錯誤: {error_msg}")
    except Exception as e:
        raise ValueError(f"航班搜尋時發生未預期的錯誤: {str(e)}")
