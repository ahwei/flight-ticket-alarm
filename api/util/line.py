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
    bubbles = []
    for offer in offers[:10]:  # 限制最多顯示10筆
        segments_contents = []

        # 遍歷所有行程（去程和回程）
        for itinerary_index, itinerary in enumerate(offer.get("itineraries", [])):
            # 加入行程標題（去程/回程）
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
            for segment in itinerary.get("segments", []):
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

            # 在去程和回程之間加入分隔
            if itinerary_index < len(offer.get("itineraries", [])) - 1:
                segments_contents.append(SeparatorComponent(margin="xl"))

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
