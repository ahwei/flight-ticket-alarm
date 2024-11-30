from flask import Blueprint
from .routes.tiger import tiger_route
from .routes.scoot import scoot_route

api_blueprint = Blueprint('api', __name__)

# 註冊子路由
api_blueprint.register_blueprint(tiger_route, url_prefix='/tiger')
api_blueprint.register_blueprint(scoot_route, url_prefix='/scoot')

api = api_blueprint
