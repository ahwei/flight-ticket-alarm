from flask import Blueprint, jsonify, request
from datetime import datetime
from typing import List, Optional

hello_route = Blueprint('hello', __name__)

@hello_route.route('/')
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
    return jsonify(message='Hello, Test!')
