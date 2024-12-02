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
from .airline import format_datetime, get_airline_info


def create_flight_flex_message(offers):
    if not offers:
        return TextSendMessage(text="沒有找到符合條件的航班")

    bubbles = []
    for offer in offers[:10]:
        # 檢查必要的資料是否存在
        if not offer.get("itineraries"):
            continue

        segments_contents = []

        # 遍歷所有行程（去程和回程）
        for itinerary_index, itinerary in enumerate(offer["itineraries"]):
            if not itinerary.get("segments"):
                continue

            # 加入行程標題
            segments_contents.extend(
                [
                    TextComponent(
                        text=f"{'去程' if itinerary_index == 0 else '回程'}",
                        size="md",
                        weight="bold",
                        color="#1DB446",
                    ),
                    SeparatorComponent(margin="sm"),
                ]
            )

            # 處理該行程的所有航段
            for segment in itinerary["segments"]:
                try:
                    airline_name, aircraft_type, flight_number = get_airline_info(
                        segment
                    )
                except Exception as e:
                    continue

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

            # 在去程和回程之間加入分隔
            if itinerary_index < len(offer["itineraries"]) - 1:
                segments_contents.append(SeparatorComponent(margin="xl"))

        # 如果沒有成功添加任何航段內容，跳過這個 offer
        if not segments_contents:
            continue

        try:
            cabin = (
                offer.get("travelerPricings", [{}])[0]
                .get("fareDetailsBySegment", [{}])[0]
                .get("cabin", "UNKNOWN")
                .capitalize()
            )
            airline_code = offer.get("validatingAirlineCodes", ["UNKNOWN"])[0]
            airline_name = AIRLINE_CODES.get(airline_code, airline_code)
            price = float(offer.get("price", {}).get("grandTotal", 0))
            seats = offer.get("numberOfBookableSeats", 0)

            bubble = BubbleContainer(
                body=BoxComponent(
                    layout="vertical",
                    contents=[
                        TextComponent(
                            text=f"{airline_name}",
                            weight="bold",
                            size="xl",
                            margin="md",
                        ),
                        TextComponent(
                            text=f"{cabin}艙 ({seats}座位)",
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
                                    text=f"總價: TWD {price:,.0f}",
                                    size="lg",
                                    weight="bold",
                                    color="#1DB446",
                                ),
                                TextComponent(
                                    text="*含稅價", size="xs", color="#888888"
                                ),
                            ],
                        ),
                    ],
                )
            )
            bubbles.append(bubble)
        except Exception as e:
            continue

    if not bubbles:
        return TextSendMessage(text="抱歉，無法處理航班資訊")

    return FlexSendMessage(
        alt_text="航班資訊",
        contents={
            "type": "carousel",
            "contents": [bubble.as_json_dict() for bubble in bubbles],
        },
    )
