"""Cienki launcher mobilnej aplikacji Refrigeration Calc."""
from __future__ import annotations


def main() -> None:
    """Uruchom aplikację KivyMD, zachowując opcjonalny import runtime."""
    from tpof.mobile.app import ShockerCalcApp

    ShockerCalcApp().run()


if __name__ == "__main__":
    main()
