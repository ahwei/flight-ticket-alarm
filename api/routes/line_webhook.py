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


def format_datetime(datetime_str):
    """格式化日期時間字串"""
    from datetime import datetime

    dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M")


def create_flight_flex_message(offers):
    bubbles = []
    for offer in offers[:10]:  # 限制最多顯示10筆
        segments_contents = []

        # 處理每個航段
        for segment in offer["itineraries"][0]["segments"]:
            segments_contents.extend(
                [
                    TextComponent(
                        text=f"✈️ {segment['carrierCode']}{segment['number']}",
                        size="md",
                        weight="bold",
                    ),
                    BoxComponent(
                        layout="vertical",
                        margin="sm",
                        spacing="sm",
                        contents=[
                            TextComponent(
                                text=f"從 {segment['departure']['iataCode']} "
                                f"{format_datetime(segment['departure']['at'])}",
                                size="sm",
                            ),
                            TextComponent(
                                text=f"到 {segment['arrival']['iataCode']} "
                                f"{format_datetime(segment['arrival']['at'])}",
                                size="sm",
                            ),
                            TextComponent(
                                text=f"飛行時間: {segment['duration'].replace('PT', '').replace('H', '小時').replace('M', '分鐘')}",
                                size="xs",
                                color="#888888",
                            ),
                        ],
                    ),
                    SeparatorComponent(margin="md"),
                ]
            )

        # 基本艙等資訊
        cabin = offer["travelerPricings"][0]["fareDetailsBySegment"][0][
            "cabin"
        ].capitalize()

        bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text=f"{offer['validatingAirlineCodes'][0]}航空",
                        weight="bold",
                        size="xl",
                        margin="md",
                    ),
                    TextComponent(
                        text=f"{cabin}艙 ({offer['numberOfBookableSeats']}座位)",
                        size="sm",
                        color="#888888",
                        margin="sm",
                    ),
                    SeparatorComponent(margin="md"),
                    BoxComponent(
                        layout="vertical",
                        margin="md",
                        spacing="sm",
                        contents=segments_contents,
                    ),
                    BoxComponent(
                        layout="vertical",
                        margin="md",
                        contents=[
                            TextComponent(
                                text=f"總價: TWD {float(offer['price']['grandTotal']):,.0f}",
                                size="lg",
                                weight="bold",
                                color="#1DB446",
                            ),
                            TextComponent(text="*含稅價", size="xs", color="#888888"),
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
