from flask import Blueprint, jsonify, request, abort, Response
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    QuickReply,
    QuickReplyButton,
    MessageAction,
)
import os
import logging
from api.util.search import (
    search_flights,
)
from api.util.line import create_flight_flex_message
from amadeus import Client
from datetime import datetime
import re


# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

line_webhook_route = Blueprint("line_webhook", __name__)


# 初始化時檢查環境變數
try:
    line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
    handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
except Exception as e:
    logger.error(f"Initialization error: {str(e)}")
    raise


# 用戶搜尋狀態儲存
user_states = {}


class SearchState:
    def __init__(self):
        self.step = "init"
        self.data = {
            "trip": None,
            "flight_data": [],
            "passengers": {
                "adults": 1,
                "children": 0,
                "infants_in_seat": 0,
                "infants_on_lap": 0,
            },
            "seat": "economy",
        }


@line_webhook_route.route("/", methods=["POST"])
@line_webhook_route.route("", methods=["POST"])
def line_webhook():
    # 檢查必要的請求頭
    if "X-Line-Signature" not in request.headers:
        logger.error("Missing X-Line-Signature header")
        return jsonify({"error": "Missing X-Line-Signature header"}), 400

    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    if not body:
        logger.error("Empty request body")
        return jsonify({"error": "Empty request body"}), 400

    logger.info(f"Received webhook body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError as e:
        logger.error(f"Invalid signature error: {str(e)}")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        if hasattr(event, "delivery_context") and event.delivery_context.is_redelivery:
            return

        user_id = event.source.user_id
        message_text = event.message.text.strip().lower()

        if message_text == "search flights":
            # 初始化搜尋
            user_states[user_id] = SearchState()
            quick_reply = QuickReply(
                items=[
                    QuickReplyButton(action=MessageAction(label="單程", text="單程")),
                    QuickReplyButton(action=MessageAction(label="來回", text="來回")),
                ]
            )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請選擇航程類型：", quick_reply=quick_reply),
            )
            return

        if user_id not in user_states:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入 'search flights' 開始搜尋航班。"),
            )
            return

        state = user_states[user_id]

        if state.step == "init":
            if message_text in ["單程", "來回"]:
                state.data["trip"] = (
                    "one-way" if message_text == "單程" else "round-trip"
                )
                state.step = "departure_date"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入出發日期 (YYYY-MM-DD)："),
                )
            return

        if state.step == "departure_date":
            if re.match(r"\d{4}-\d{2}-\d{2}", message_text):
                flight_data = {
                    "date": message_text,
                    "from_airport": None,
                    "to_airport": None,
                }
                state.data["flight_data"].append(flight_data)
                state.step = "from_airport"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入出發機場代碼（如：TPE）："),
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="日期格式不正確，請使用 YYYY-MM-DD 格式："),
                )
            return

        if state.step == "from_airport":
            if re.match(r"^[A-Z]{3}$", message_text.upper()):
                state.data["flight_data"][0]["from_airport"] = message_text.upper()
                state.step = "to_airport"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入目的地機場代碼（如：NRT）："),
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入正確的機場代碼（3個大寫字母）："),
                )
            return

        if state.step == "to_airport":
            if re.match(r"^[A-Z]{3}$", message_text.upper()):
                state.data["flight_data"][0]["to_airport"] = message_text.upper()
                if state.data["trip"] == "round-trip":
                    state.step = "return_date"
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="請輸入回程日期 (YYYY-MM-DD)："),
                    )
                else:
                    state.step = "search"
                    execute_search(event.reply_token, state.data)
                    del user_states[user_id]
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入正確的機場代碼（3個大寫字母）："),
                )
            return

        if state.step == "return_date":
            if re.match(r"\d{4}-\d{2}-\d{2}", message_text):
                return_flight = {
                    "date": message_text,
                    "from_airport": state.data["flight_data"][0]["to_airport"],
                    "to_airport": state.data["flight_data"][0]["from_airport"],
                }
                state.data["flight_data"].append(return_flight)
                state.step = "search"
                execute_search(event.reply_token, state.data)
                del user_states[user_id]
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="日期格式不正確，請使用 YYYY-MM-DD 格式："),
                )
            return

    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        if not event.delivery_context.is_redelivery:
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="抱歉，處理您的請求時發生錯誤。請稍後再試。"),
                )
            except Exception as reply_error:
                logger.error(f"Error sending error message: {str(reply_error)}")


def execute_search(reply_token, search_data):
    try:
        amadeus = Client(
            client_id=os.getenv("AMADEUS_API_KEY"),
            client_secret=os.getenv("AMADEUS_API_SECRET"),
        )

        if not amadeus.client_id or not amadeus.client_secret:
            raise ValueError("Amadeus API 認證資訊未設定")

        offers, _ = search_flights(search_data, amadeus)

        if not offers:
            line_bot_api.reply_message(
                reply_token,
                TextSendMessage(text="目前沒有找到符合的航班，請嘗試其他日期或航線。"),
            )
            return

        flex_message = create_flight_flex_message(offers)
        line_bot_api.reply_message(reply_token, flex_message)

    except Exception as e:
        logger.error(f"Search execution error: {str(e)}")
        line_bot_api.reply_message(
            reply_token, TextSendMessage(text=f"搜尋航班時發生錯誤：{str(e)}")
        )
