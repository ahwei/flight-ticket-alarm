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

# 新增航空公司對照表
AIRLINE_CODES = {
    "TW": "台灣虎航",
    "BR": "長榮航空",
    "CI": "中華航空",
    "JL": "日本航空",
    "NH": "全日空航空",
    "MM": "樂桃航空",
    "VJ": "越捷航空",
    "JX": "星宇航空",
    "AK": "亞洲航空",
}

# 新增機型對照表
AIRCRAFT_CODES = {
    "738": "波音 737-800",
    "333": "空巴 A330-300",
    "359": "空巴 A350-900",
    "32N": "空巴 A320neo",
    "321": "空巴 A321",
    "320": "空巴 A320",
    "789": "波音 787-9",
    "788": "波音 787-8",
}

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


def get_airline_info(segment):
    """安全地取得航空公司和機型資訊"""
    try:
        carrier_code = segment.get("carrierCode", "")
        aircraft_info = segment.get("aircraft", {})
        aircraft_code = (
            aircraft_info.get("code", "") if isinstance(aircraft_info, dict) else ""
        )

        # 確保代碼不為空
        if not carrier_code:
            carrier_code = "未知航空"
        if not aircraft_code:
            aircraft_code = "未知機型"

        airline_name = AIRLINE_CODES.get(carrier_code, f"其他航空({carrier_code})")
        aircraft_type = AIRCRAFT_CODES.get(aircraft_code, f"其他機型({aircraft_code})")

        return airline_name, aircraft_type, carrier_code
    except Exception as e:
        logger.error(f"Error processing airline info: {str(e)}")
        return "未知航空", "未知機型", "N/A"


def create_flight_flex_message(offers):
    bubbles = []
    for offer in offers[:10]:  # 限制最多顯示10筆
        segments_contents = []

        # 處理每個航段
        for segment in offer.get("itineraries", [{}])[0].get("segments", []):
            # 使用新的安全取得航空公司和機型資訊的函數
            airline_name, aircraft_type, flight_number = get_airline_info(segment)

            segments_contents.extend(
                [
                    TextComponent(
                        text=f"✈️ {airline_name} {segment.get('number', 'N/A')}",
                        size="md",
                        weight="bold",
                    ),
                    TextComponent(
                        text=f"機型: {aircraft_type}",
                        size="xs",
                        color="#888888",
                        margin="sm",
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

        cabin = offer["travelerPricings"][0]["fareDetailsBySegment"][0][
            "cabin"
        ].capitalize()
        airline_code = offer["validatingAirlineCodes"][0]
        airline_name = AIRLINE_CODES.get(airline_code, airline_code)

        bubble = BubbleContainer(
            body=BoxComponent(
                layout="vertical",
                contents=[
                    TextComponent(
                        text=f"{airline_name}", weight="bold", size="xl", margin="md"
                    ),
                    # ...rest of the bubble content remains the same...
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
