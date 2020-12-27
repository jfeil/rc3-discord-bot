from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib import request
import json

class SchedulePlanner:

    json_url: str
    data: Dict[str, Any]

    def __init__(self, json_url) -> None:
        self.json_url = json_url
        self.data = {}
        self.update()

    def update(self) -> None:
        data = json.loads(request.urlopen(self.json_url).read().decode())
        if not self.data or self.data["version"] != data["schedule"]["version"]:
            self.data = data["schedule"]
        pass

    def current_events(self, date: datetime = None):
        if not date:
            date = datetime.now(tz=timezone(timedelta(seconds=3600)))

        first_day = 27

        current_events = {}
        nextup_events = {}

        day = date.day - first_day
        if day < 0:
            date.replace(day=first_day, hour=0, minute=0)
        if day > 4:
            return []

        for room in self.data["conference"]["days"][day]["rooms"]:
            room_element = self.data["conference"]["days"][day]["rooms"][room]
            for event in room_element:
                event_date = datetime.fromisoformat(event["date"])
                duration = datetime.strptime(event["duration"], "%H:%M")
                duration = timedelta(hours=duration.hour, minutes=duration.minute)
                if date > event_date and date < event_date + duration:
                    current_events[room] = event
                if date < event_date:
                    nextup_events[room] = event
                    break

        return (current_events, nextup_events)