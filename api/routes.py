from flask import jsonify
from . import api_blueprint as api

@api.route('/hello')
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
    return jsonify(message='Hello, World!')

@api.route('/flights')
def get_flights():
    """
    取得航班資訊
    ---
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
                  id:
                    type: integer
                  from:
                    type: string
                  to:
                    type: string
                  price:
                    type: number
    """
    flights = [
        {"id": 1, "from": "TPE", "to": "ICN", "price": 7000},
        {"id": 2, "from": "TPE", "to": "NRT", "price": 8000}
    ]
    return jsonify(flights=flights)
