from flask import Blueprint, jsonify, request, abort, Response
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import logging
from api.util.search import search_flights_simple
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
        message_text = event.message.text
        logger.info(f"Processing message: {message_text}")

        try:
            amadeus = Client(
                client_id=os.getenv("AMADEUS_API_KEY"),
                client_secret=os.getenv("AMADEUS_API_SECRET"),
            )

            offers = search_flights_simple(amadeus)
            if not offers:
                raise ValueError("No flight offers found")

            response_messages = [TextSendMessage(text="Here are the flight offers:")]
            response_messages.extend(
                [TextSendMessage(text=str(offer)) for offer in offers]
            )

            line_bot_api.reply_message(event.reply_token, response_messages)
        except Exception as e:
            logger.error(f"Flight search error: {str(e)}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Sorry, there was an error searching for flights."
                ),
            )

    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，處理您的請求時發生錯誤。"),
            )
        except Exception as reply_error:
            logger.error(f"Error sending error message: {str(reply_error)}")
