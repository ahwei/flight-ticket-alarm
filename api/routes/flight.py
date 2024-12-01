from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import List, Optional
from amadeus import Client, ResponseError
import os
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


# 初始化 Flask Blueprint
flight_route = Blueprint('flight', __name__)

# 初始化 Amadeus 客户端
amadeus = Client(
    client_id=os.getenv('AMADEUS_API_KEY'),
    client_secret=os.getenv('AMADEUS_API_SECRET')
)


@flight_route.route('/')
def hello_world():
    return jsonify({
        "search_criteria": {
            "flight_data": [
                {
                    "date": "YYYY-MM-DD",
                    "from_airport": "出發機場代碼",
                    "to_airport": "抵達機場代碼"
                }
            ],
            "trip": ["one-way", "round-trip"],
            "seat": ["economy", "premium-economy", "business", "first"],
            "passengers": {
                "adults": "成人人數",
                "children": "兒童人數",
                "infants_in_seat": "佔位嬰兒人數",
                "infants_on_lap": "抱嬰兒人數"
            }
        }
    })


@flight_route.route('/search', methods=['POST'])
def search():
    data = request.get_json()

    # 預設值設定
    default_flight_data = [
        FlightData(
            date=datetime.now().strftime("%Y-%m-%d"),
            from_airport="TPE",
            to_airport="NRT"
        )
    ]

    # 從請求中取得資料，如果沒有則使用預設值
    flight_data_raw = data.get('flight_data', [])
    flight_data = [
        FlightData(
            date=f.get('date'),
            from_airport=f.get('from_airport'),
            to_airport=f.get('to_airport')
        ) for f in flight_data_raw
    ] if flight_data_raw else default_flight_data

    passengers_data = data.get('passengers', {})
    passengers = Passengers(
        adults=int(passengers_data.get('adults', 1)),
        children=int(passengers_data.get('children', 0)),
        infants_in_seat=int(passengers_data.get('infants_in_seat', 0)),
        infants_on_lap=int(passengers_data.get('infants_on_lap', 0))
    )

    trip = data.get('trip', 'one-way')
    seat = data.get('seat', 'economy')

    # 映射座位等級到 Amadeus 的 travelClass
    seat_mapping = {
        'economy': 'ECONOMY',
        'premium-economy': 'PREMIUM_ECONOMY',
        'business': 'BUSINESS',
        'first': 'FIRST'
    }
    travel_class = seat_mapping.get(seat.lower(), 'ECONOMY')

    # 獲取出發和返回日期
    departureDate = None
    returnDate = None

    if len(flight_data) >= 1:
        departureDate = flight_data[0].date

    if trip == 'round-trip' and len(flight_data) >= 2:
        returnDate = flight_data[1].date
    elif trip == 'round-trip' and len(flight_data) == 1:
        returnDate = data.get('return_date')
        if not returnDate:
            return jsonify({'error': 'Round-trip requires a return date'}), 400

    originLocationCode = flight_data[0].from_airport
    destinationLocationCode = flight_data[0].to_airport

    # 計算乘客人數
    adults = passengers.adults
    children = passengers.children
    infants = passengers.infants_in_seat + passengers.infants_on_lap

    # 構建搜尋參數
    search_params = {
        'originLocationCode': originLocationCode,
        'destinationLocationCode': destinationLocationCode,
        'departureDate': departureDate,
        'adults': adults,
        'travelClass': travel_class,
        'currencyCode': 'TWD',  # 您可以根據需要修改貨幣代碼
    }

    if returnDate:
        search_params['returnDate'] = returnDate

    if children > 0:
        search_params['children'] = children

    if infants > 0:
        search_params['infants'] = infants

    # 調用 Amadeus API 獲取航班報價
    try:
        response = amadeus.shopping.flight_offers_search.get(**search_params)
        offers = response.data
    except ResponseError as error:
        return jsonify({'error': str(error)}), 500

    # 返回結果
    return jsonify({
        "data": offers,
        "search_criteria": {
            "flight_data": [
                {
                    "date": fd.date,
                    "from_airport": fd.from_airport,
                    "to_airport": fd.to_airport
                } for fd in flight_data
            ],
            "trip": trip,
            "seat": seat,
            "passengers": passengers.__dict__
        }
    })
