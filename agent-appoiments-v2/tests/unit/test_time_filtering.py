"""Test time-of-day availability filtering."""
import pytest
from datetime import datetime
from src.availability import TimeFilter, TimeOfDay


class TestTimeFiltering:
    """Test filtering slots by time of day."""

    @pytest.fixture
    def sample_slots(self):
        """Sample availability slots."""
        return [
            {"date": "2025-01-15", "start_time": "09:00", "end_time": "09:30"},
            {"date": "2025-01-15", "start_time": "10:00", "end_time": "10:30"},
            {"date": "2025-01-15", "start_time": "14:00", "end_time": "14:30"},
            {"date": "2025-01-15", "start_time": "16:00", "end_time": "16:30"},
            {"date": "2025-01-16", "start_time": "09:00", "end_time": "09:30"},
            {"date": "2025-01-16", "start_time": "15:00", "end_time": "15:30"},
        ]

    def test_filter_morning_slots(self, sample_slots):
        """Filter for morning slots only (before 12:00)."""
        filter = TimeFilter()

        result = filter.filter_by_time_of_day(sample_slots, TimeOfDay.MORNING)

        assert len(result) == 3  # 3 morning slots
        assert all(
            int(slot["start_time"].split(":")[0]) < 12
            for slot in result
        )

    def test_filter_afternoon_slots(self, sample_slots):
        """Filter for afternoon slots only (12:00+)."""
        filter = TimeFilter()

        result = filter.filter_by_time_of_day(sample_slots, TimeOfDay.AFTERNOON)

        assert len(result) == 3  # 3 afternoon slots
        assert all(
            int(slot["start_time"].split(":")[0]) >= 12
            for slot in result
        )

    def test_limit_to_next_3_days(self, sample_slots):
        """Show only next 3 available days."""
        filter = TimeFilter()

        result = filter.limit_to_next_days(sample_slots, max_days=3)

        unique_dates = set(slot["date"] for slot in result)
        assert len(unique_dates) <= 3
