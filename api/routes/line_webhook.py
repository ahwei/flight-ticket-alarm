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
    # 限制最多顯示10筆資料
    for offer in offers[:10]:
        bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text="航班資訊", weight="bold", size="xl", margin="md"
                    ),
                    SeparatorComponent(margin="xxl"),
                    BoxComponent(
                        layout="vertical",
                        margin="xxl",
                        spacing="sm",
                        contents=[
                            TextComponent(
                                text=f"航空公司: {offer.get('carrier_name', 'N/A')}",
                                size="md",
                                wrap=True,
                            ),
                            TextComponent(
                                text=f"航班號碼: {offer.get('flight_number', 'N/A')}",
                                size="md",
                            ),
                            TextComponent(
                                text=f"出發: {offer.get('departure_time', 'N/A')}",
                                size="md",
                            ),
                            TextComponent(
                                text=f"抵達: {offer.get('arrival_time', 'N/A')}",
                                size="md",
                            ),
                            SeparatorComponent(margin="md"),
                            TextComponent(
                                text=f"起點: {offer.get('origin', 'N/A')}", size="sm"
                            ),
                            TextComponent(
                                text=f"終點: {offer.get('destination', 'N/A')}",
                                size="sm",
                            ),
                            TextComponent(
                                text=f"價格: {offer.get('price', 'N/A')}",
                                size="lg",
                                weight="bold",
                                color="#1DB446",
                                margin="md",
                            ),
                        ],
                    ),
                ],
            )
        )
        bubbles.append(bubble)

    return FlexSendMessage(
        alt_text="航班資訊",
        contents={
            "type": "carousel",
            "contents": [bubble.as_json_dict() for bubble in bubbles],
        },
    )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    try:
        # 檢查是否為重新傳遞的訊息
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
                if not event.delivery_context.is_redelivery:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(
                            text=f"抱歉，查詢航班時發生{str(e)}。請稍後再試。"
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
