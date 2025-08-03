from datetime import datetime, timedelta, timezone

import pytest

from src.core.utilities import DEFAULT_TZ, datetime_from_iso8601, get_logger

log = get_logger(__name__)


class Test_datetime_from_iso8601:
    def test_parse_utc(self):
        dt = datetime_from_iso8601("2023-08-03T12:34:56Z")
        assert dt == datetime(2023, 8, 3, 12, 34, 56, tzinfo=DEFAULT_TZ)

    def test_parse_offset_positive(self):
        dt = datetime_from_iso8601("2023-08-03T12:34:56+05:30")

        assert dt
        assert dt.utcoffset() == timedelta(hours=5, minutes=30)

    def test_parse_offset_negative(self):
        dt = datetime_from_iso8601("2023-08-03T23:45:00-07:00")

        assert dt
        assert dt.utcoffset() == timedelta(hours=-7)

    def test_parse_naive(self):
        dt = datetime_from_iso8601("2023-08-03T12:34:56")

        assert dt
        assert dt == datetime(2023, 8, 3, 12, 34, 56, tzinfo=DEFAULT_TZ)

    def test_parse_milliseconds(self):
        dt = datetime_from_iso8601("2023-08-03T12:34:56.789Z")

        assert dt
        assert dt.microsecond == 789000

    def test_parse_microseconds(self):
        dt = datetime_from_iso8601("2023-08-03T12:34:56.789123Z")

        assert dt
        assert dt.microsecond == 789123

    def test_parse_midnight(self):
        dt = datetime_from_iso8601("2023-08-03T00:00:00Z")

        assert dt
        assert dt.hour == 0 and dt.minute == 0 and dt.second == 0

    def test_parse_leap_year(self):
        dt = datetime_from_iso8601("2024-02-29T15:00:00Z")

        assert dt
        assert dt.year == 2024 and dt.month == 2 and dt.day == 29

    def test_ddmmyy_hh_mm_ss(self):
        dt = datetime_from_iso8601("2023/08/03 12:34:56")

        assert dt
        assert dt.year == 2023 and dt.month == 8 and dt.day == 3 and dt.hour == 12 and dt.minute == 34

    def test_invalid_dt(self):
        assert not datetime_from_iso8601("2023/08/03X12:34:56")

    def test_empty_string(self):
        assert not datetime_from_iso8601("")

    def test_date_only(self):
        dt = datetime_from_iso8601("2023-08-03")

        assert dt
        assert dt.year == 2023 and dt.month == 8 and dt.day == 3
        # Depending on your design, dt could be midnight and tz-naive

    def test_missing_seconds(self):
        dt = datetime_from_iso8601("2023-08-03T12:34Z")

        assert dt
        assert dt.hour == 12 and dt.minute == 34 and dt.second == 0
        assert dt.hour == 12 and dt.minute == 34 and dt.second == 0
        assert dt.hour == 12 and dt.minute == 34 and dt.second == 0
        assert dt.hour == 12 and dt.minute == 34 and dt.second == 0
