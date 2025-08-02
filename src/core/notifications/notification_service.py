from enum import Enum

import requests


class PriorityEnum(str, Enum):
    urgent = "urgent"
    high = "high"
    default = "default"
    low = "low"
    min = "min"

    def __str__(self) -> str:
        return str.__str__(self)


def send_notification(
    message: str,
    title: str = "",
    priority: PriorityEnum = PriorityEnum.default,
    tags: str = "",
):
    topic: str = "zhuhome_mpnl"
    headers = {}

    if title:
        headers["Title"] = title
    if priority:
        headers["Priority"] = priority
    if tags:
        headers["Tags"] = tags

    requests.post(
        f"https://ntfy.sh/{topic}",
        data=message.encode(encoding="utf-8"),
        headers=headers,
    )


if __name__ == "__main__":
    send_notification(message="hello!", title="test message")
