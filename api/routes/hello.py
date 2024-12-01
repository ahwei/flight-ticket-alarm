from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import List, Optional
from fast_flights import FlightData, Passengers, create_filter, get_flights

hello_route = Blueprint('hello', __name__)

@hello_route.route('/')
def hello_world():
    # Create a new filter
    filter = create_filter(
        flight_data=[
            # Include more if it's not a one-way trip
            FlightData(
                date="2024-12-13",  # Date of departure
                from_airport="TPE", 
                to_airport="NRT"
            ),
            # ... include more for round trips
        ],
        trip="one-way",  # Trip (round-trip, one-way)
        seat="economy",  # Seat (economy, premium-economy, business or first)
        passengers=Passengers(
            adults=2,
            children=1,
            infants_in_seat=0,
            infants_on_lap=0
        ),
    )

    # Get flights with a filter
    result = get_flights(filter)

    # The price is currently... low/typical/high
    return jsonify({
        "data": result,
        "search_criteria": {
            "flight_data": [
                {
                    "date": "2024-12-13",
                    "from_airport": "TPE",
                    "to_airport": "NRT"
                }
            ],
            "trip": "one-way",
            "seat": "economy",
            "passengers": {
                "adults": 2,
                "children": 1,
                "infants_in_seat": 0,
                "infants_on_lap": 0
            }
        }
    })

 
  
