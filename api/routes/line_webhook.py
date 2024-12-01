from flask import Blueprint, jsonify, request, abort, Response
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

line_webhook_route = Blueprint("line_webhook", __name__)

# 初始化 Line Bot API 和 handler
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))


@line_webhook_route.route("/", methods=["POST"])
def line_webhook():
    # 確認標頭是否存在
    signature = request.headers["X-Line-Signature"]

    # 獲取請求體
    body = request.get_data(as_text=True)
    logger.info(f"Received webhook body: {body}")

    try:
        # 處理訊息事件
        handler.handle(body, signature)
        return jsonify({"message": "OK"}), 200
    except InvalidSignatureError:
        logger.error(f"InvalidSignatureError: {InvalidSignatureError}")
        abort(400, description="Invalid signature")


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 處理文字訊息
    message_text = event.message.text
    logger.info(f"Received message: {message_text}")

    # 簡單回覆相同訊息
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=message_text))
