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
    "TR": "酷航",
}

# 新增機型對照表
AIRCRAFT_CODES = {
    "738": "波音 737-800",
    "747": "波音 747",
    "744": "波音 747-400",
    "748": "波音 747-800",
    "333": "空巴 A330-300",
    "359": "空巴 A350-900",
    "32N": "空巴 A320neo",
    "321": "空巴 A321",
    "32Q": "空巴 A321neo",
    "320": "空巴 A320",
    "789": "波音 787-9",
    "788": "波音 787-8",
    "77W": "波音 777-300ER",
    "772": "波音 777-200",
    "773": "波音 777-300",
    "773": "波音 777-300",
    "330": "空巴 A330",
    "332": "空巴 A330-200",
    "346": "空巴 A340-600",
    "359": "空巴 A350-900",
    "35K": "空巴 A350-1000",
    "380": "空巴 A380",
}


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
