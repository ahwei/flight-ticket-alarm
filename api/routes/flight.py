from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import List, Optional
from amadeus import Client, ResponseError
import os
from api.util.search import search_flights, search_flights_simple


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


# 初始化 Flask Blueprint
flight_route = Blueprint("flight", __name__)

# 初始化 Amadeus 客戶端
amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET"),
)


@flight_route.route("/")
def hello_world():
    offers = search_flights_simple(amadeus)

    return jsonify(
        {
            "data": offers,
            "search_criteria": {
                "flight_data": [
                    {
                        "date": "YYYY-MM-DD",
                        "from_airport": "出發機場代碼",
                        "to_airport": "抵達機場代碼",
                    }
                ],
                "trip": ["one-way", "round-trip"],
                "seat": ["economy", "premium-economy", "business", "first"],
                "passengers": {
                    "adults": "成人人數",
                    "children": "兒童人數",
                    "infants_in_seat": "佔位嬰兒人數",
                    "infants_on_lap": "抱嬰兒人數",
                },
            },
        }
    )


@flight_route.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    try:
        offers, search_criteria = search_flights(data, amadeus)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except ResponseError as error:
        return jsonify({"error": str(error)}), 500

    return jsonify({"data": offers, "search_criteria": search_criteria})
