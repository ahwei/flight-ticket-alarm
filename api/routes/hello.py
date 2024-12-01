from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import List, Optional
from fast_flights import FlightData, Passengers, create_filter, get_flights

hello_route = Blueprint('hello', __name__)

@hello_route.route('/')
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

@hello_route.route('/search', methods=['POST'])
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
        adults=passengers_data.get('adults', 1),
        children=passengers_data.get('children', 0),
        infants_in_seat=passengers_data.get('infants_in_seat', 0),
        infants_on_lap=passengers_data.get('infants_on_lap', 0)
    )

    # 建立搜尋過濾器
    filter = create_filter(
        flight_data=flight_data,
        trip=data.get('trip', 'one-way'),
        seat=data.get('seat', 'economy'),
        passengers=passengers
    )

    # 取得航班資訊
    result = get_flights(filter)

    # 修改 passengers 屬性引用
    return jsonify({
        "data": result,
        "search_criteria": {
            "flight_data": [
                {
                    "date": fd.date,
                    "from_airport": fd.from_airport,
                    "to_airport": fd.to_airport
                } for fd in flight_data
            ],
            "trip": filter.trip,
            "seat": filter.seat,
            "passengers": passengers.__dict__  # 使用 __dict__ 來取得所有屬性
        }
    })



