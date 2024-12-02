from flask import Blueprint, jsonify, request, abort, Response
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
)
import os
import logging
from api.util.search import search_flights_simple
from api.util.line import create_flight_flex_message
from amadeus import Client


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
            logger.warning("This is a redelivered message, skipping reply")
            return

        message_text = event.message.text.strip().lower()
        logger.info(f"Processing message: {message_text}")

        if message_text == "search flights":
            try:
                amadeus = Client(
                    client_id=os.getenv("AMADEUS_API_KEY"),
                    client_secret=os.getenv("AMADEUS_API_SECRET"),
                )

                if not amadeus.client_id or not amadeus.client_secret:
                    raise ValueError("Amadeus API 認證資訊未設定")

                offers = search_flights_simple(amadeus)
                if not offers:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="目���沒有找到符合的航班，請稍後再試。"),
                    )
                    return

                flex_message = create_flight_flex_message(offers)
                line_bot_api.reply_message(event.reply_token, flex_message)

            except ValueError as ve:
                logger.error(f"Flight search value error: {str(ve)}")
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage(text=str(ve))
                )
            except Exception as e:
                logger.error(f"Flight search error: {str(e)}", exc_info=True)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="抱歉，查詢航班時發生錯誤。請確認航班資訊是否正確。"
                    ),
                )
        else:
            # 如果不是搜尋航班的指令，回覆使用說明
            if not event.delivery_context.is_redelivery:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入 'search flights' 來搜尋航班。"),
                )

    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        # 只在非重新傳遞的情況下嘗試發送錯誤訊息
        if not event.delivery_context.is_redelivery:
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="抱歉，處理您的請求時發生錯誤。請稍後再試。"),
                )
            except Exception as reply_error:
                logger.error(f"Error sending error message: {str(reply_error)}")
