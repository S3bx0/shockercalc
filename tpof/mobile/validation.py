"""Mobile input parsing and validation helpers."""


def _numeric_input_filter(value: str, _from_undo: bool = False) -> str:
    """Pozwala wpisywac liczby z polskim przecinkiem i znakiem minus."""
    return "".join(char for char in str(value) if char in "0123456789-.,")
