from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import List, Optional
from api.models.flight import Flight  # 修改引用路徑
from services.scrapers.scoot_scraper import ScootScraper

scoot_route = Blueprint("scoot", __name__)
scoot_scraper = ScootScraper()


@scoot_route.route("/hello")
def hello_world():
    """
    簡單的測試 API
    ---
    responses:
      200:
        description: 成功的回應
        schema:
          properties:
            message:
              type: string
              example: "Hello, World!"
    """
    return jsonify(message="Hello, World!")


@scoot_route.route("/search")
async def search_flights():
    """
    搜尋酷航航班
    ---
    parameters:
      - name: from
        in: query
        type: string
        required: true
        description: 出發地機場代碼
      - name: to
        in: query
        type: string
        required: true
        description: 目的地機場代碼
      - name: date
        in: query
        type: string
        required: true
        description: 出發日期 (YYYY-MM-DD)
    responses:
      200:
        description: 航班列表
        schema:
          properties:
            flights:
              type: array
              items:
                type: object
                properties:
                  flight_number:
                    type: string
                  departure:
                    type: string
                  arrival:
                    type: string
                  departure_time:
                    type: string
                    format: date-time
                  arrival_time:
                    type: string
                    format: date-time
                  price:
                    type: number
                  currency:
                    type: string
                  airline:
                    type: string
                  available_seats:
                    type: integer
    """
    from_airport = request.args.get("from")
    to_airport = request.args.get("to")
    date = datetime.strptime(request.args.get("date"), "%Y-%m-%d")

    try:
        flights = await scoot_scraper.search_flights(from_airport, to_airport, date)
        return jsonify({"flights": [vars(f) for f in flights]})
    except NotImplementedError:
        return jsonify({"message": "Scoot Airways search endpoint - Not implemented"})
