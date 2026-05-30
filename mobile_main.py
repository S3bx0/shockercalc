"""Launcher dla python-for-android / Buildozer.

p4a domyślnie wykonuje `main.py` z katalogu projektu po starcie aplikacji.
Ten plik tylko deleguje do `tpof.mobile.main:main`.
"""
from tpof.mobile.main import main

if __name__ == "__main__":
    main()

