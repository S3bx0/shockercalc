"""Testy jednostkowe walidatorów (pure functions)."""

from tpof.core.validators import (
    MAX_TEMPERATURE_C,
    MIN_TEMPERATURE_C,
    is_positive_number,
    is_valid_temperature,
    parse_number,
)


class TestParseNumber:
    def test_int(self):
        assert parse_number(5) == 5.0

    def test_float(self):
        assert parse_number(3.14) == 3.14

    def test_string_dot(self):
        assert parse_number("2.5") == 2.5

    def test_string_comma(self):
        assert parse_number("2,5") == 2.5

    def test_with_whitespace(self):
        assert parse_number("  -1,75 ") == -1.75

    def test_none(self):
        assert parse_number(None) is None

    def test_garbage(self):
        assert parse_number("abc") is None

    def test_empty(self):
        assert parse_number("") is None


class TestIsPositiveNumber:
    def test_positive(self):
        assert is_positive_number(1) is True
        assert is_positive_number("3,5") is True

    def test_zero(self):
        assert is_positive_number(0) is False

    def test_negative(self):
        assert is_positive_number(-1) is False

    def test_garbage(self):
        assert is_positive_number("xyz") is False


class TestIsValidTemperature:
    def test_room_temp(self):
        assert is_valid_temperature(20) is True

    def test_freezer(self):
        assert is_valid_temperature(-18) is True

    def test_zero_accepted(self):
        # poprzednia wersja `not all(...)` odrzucała 0 — regression test
        assert is_valid_temperature(0) is True

    def test_min_bound(self):
        assert is_valid_temperature(MIN_TEMPERATURE_C) is True

    def test_below_min(self):
        assert is_valid_temperature(-300) is False

    def test_max_bound(self):
        assert is_valid_temperature(MAX_TEMPERATURE_C) is True

    def test_above_max(self):
        assert is_valid_temperature(500) is False

    def test_garbage(self):
        assert is_valid_temperature("hot") is False
