from flask import Blueprint, jsonify, request, abort, Response
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage,
    BubbleContainer,
    BoxComponent,
    TextComponent,
    ButtonComponent,
    SeparatorComponent,
)
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


def create_flight_flex_message(offers):
    bubbles = []
    for offer in offers:
        bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="Flight Offer", weight="bold", size="xl", margin="md"
                    ),
                    SeparatorComponent(margin="xxl"),
                    BoxComponent(
                        layout="vertical",
                        margin="xxl",
                        spacing="sm",
                        contents=[
                            TextComponent(text=f"Price: {offer.get('price', 'N/A')}"),
                            TextComponent(text=f"From: {offer.get('origin', 'N/A')}"),
                            TextComponent(
                                text=f"To: {offer.get('destination', 'N/A')}"
                            ),
                            TextComponent(text=f"Date: {offer.get('date', 'N/A')}"),
                        ],
                    ),
                ],
            )
        )
        bubbles.append(bubble)

    return FlexSendMessage(
        alt_text="Flight Offers",
        contents={
            "type": "carousel",
            "contents": [bubble.dict() for bubble in bubbles],
        },
    )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        message_text = event.message.text.strip().lower()
        logger.info(f"Processing message: {message_text}")

        # 只有當訊息是 "search flights" 時才進行搜尋
        if message_text == "search flights":
            try:
                amadeus = Client(
                    client_id=os.getenv("AMADEUS_API_KEY"),
                    client_secret=os.getenv("AMADEUS_API_SECRET"),
                )

                offers = search_flights_simple(amadeus)
                if not offers:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text="目前沒有找到符合的航班。"),
                    )
                    return

                flex_message = create_flight_flex_message(offers)
                line_bot_api.reply_message(event.reply_token, flex_message)

            except Exception as e:
                logger.error(f"Flight search error: {str(e)}")
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="抱歉，查詢航班時發生錯誤。請稍後再試。"),
                )
        else:
            # 如果不是搜尋航班的指令，回覆使用說明
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="請輸入 'search flights' 來搜尋航班。"),
            )

    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，處理您的請求時發生錯誤。請稍後再試。"),
            )
        except Exception as reply_error:
            logger.error(f"Error sending error message: {str(reply_error)}")
            raise
