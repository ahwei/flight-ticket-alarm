from flask import Flask, send_file, jsonify, request, abort
from flask_swagger_ui import get_swaggerui_blueprint
from api import api_blueprint
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify(message="Hello Flight Alarm")


# 註冊 API blueprint
app.register_blueprint(api_blueprint, url_prefix="/api")

# Swagger 設定
SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.yml"
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, API_URL, config={"app_name": "Flight Ticket Alarm API"}
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


# 靜態檔案路由
@app.route("/static/swagger.yml")
def send_swagger_yml():
    return send_file("swagger.yml")


# Cron job 路由
@app.route("/cron-job")
def cron_job():
    if request.remote_addr not in ["127.0.0.1", "localhost"]:
        abort(403)

    return jsonify(message="Cron job executed")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3310, debug=True)
