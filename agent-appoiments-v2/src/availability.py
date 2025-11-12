"""Availability filtering and formatting (v1.2).

New Feature: Time-of-day filtering
- Ask user preference: morning, afternoon, or any
- Filter slots accordingly
- Show only next 3 days (not overwhelming)
"""
from enum import Enum
from typing import List, Dict, Any
from datetime import datetime


class TimeOfDay(str, Enum):
    """Time of day preferences."""
    MORNING = "morning"  # Before 12:00
    AFTERNOON = "afternoon"  # 12:00 and after
    ANY = "any"


class TimeFilter:
    """Filter availability slots by time of day."""

    MORNING_CUTOFF = 12  # 12:00 (noon)

    def filter_by_time_of_day(
        self,
        slots: List[Dict[str, Any]],
        preference: TimeOfDay
    ) -> List[Dict[str, Any]]:
        """
        Filter slots by time of day preference.

        Args:
            slots: Available slots
            preference: Morning, afternoon, or any

        Returns:
            Filtered slots
        """
        if preference == TimeOfDay.ANY:
            return slots

        filtered = []
        for slot in slots:
            hour = int(slot["start_time"].split(":")[0])

            if preference == TimeOfDay.MORNING and hour < self.MORNING_CUTOFF:
                filtered.append(slot)
            elif preference == TimeOfDay.AFTERNOON and hour >= self.MORNING_CUTOFF:
                filtered.append(slot)

        return filtered

    def limit_to_next_days(
        self,
        slots: List[Dict[str, Any]],
        max_days: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Limit slots to next N unique days.

        Args:
            slots: Available slots
            max_days: Maximum number of days to show

        Returns:
            Limited slots (up to max_days unique dates)
        """
        seen_dates = set()
        limited = []

        for slot in slots:
            date = slot["date"]

            if date not in seen_dates:
                if len(seen_dates) >= max_days:
                    break
                seen_dates.add(date)

            limited.append(slot)

        return limited

    def format_slots_grouped(
        self,
        slots: List[Dict[str, Any]]
    ) -> str:
        """
        Format slots grouped by date (user-friendly).

        Args:
            slots: Filtered slots

        Returns:
            Formatted string

        Example:
            📅 Monday, January 15:
               • 9:00 AM - 9:30 AM
               • 10:00 AM - 10:30 AM

            📅 Tuesday, January 16:
               • 2:00 PM - 2:30 PM
        """
        if not slots:
            return "❌ No available slots found for your preference."

        grouped = {}
        for slot in slots:
            date = slot["date"]
            if date not in grouped:
                grouped[date] = []
            grouped[date].append(slot)

        result = "📅 Available times:\n\n"

        for date, day_slots in list(grouped.items())[:3]:  # Max 3 days
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            result += f"📅 {date_obj.strftime('%A, %B %d')}:\n"

            for slot in day_slots[:4]:  # Max 4 slots per day
                start = self._format_time_12h(slot["start_time"])
                end = self._format_time_12h(slot["end_time"])
                result += f"   • {start} - {end}\n"

            result += "\n"

        return result.strip()

    @staticmethod
    def _format_time_12h(time_24h: str) -> str:
        """Convert 24h time to 12h format."""
        hour, minute = map(int, time_24h.split(":"))
        period = "AM" if hour < 12 else "PM"
        hour_12 = hour if hour <= 12 else hour - 12
        hour_12 = 12 if hour_12 == 0 else hour_12
        return f"{hour_12}:{minute:02d} {period}"
