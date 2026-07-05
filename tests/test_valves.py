"""Testy obliczeń zaworów dekompresyjnych."""

import dataclasses
import math

import pytest

from tpof.core.valves import (
    F_MAX,
    TEMP_MAX,
    TEMP_MIN,
    V_MAX,
    ZAWORY,
    K,
    calculate_decompression_valves,
)


class TestCalculateDecompressionValves:
    def test_maxi_elebar_typowy_przypadek(self):
        res = calculate_decompression_valves(
            V=100.0, temp_przed=20.0, temp_za=-30.0, F=2.0,
            typ_zaworu="Maxi Elebar",
        )

        DT1 = 20.0 - (-30.0)  # 50
        delta_T = (2.0 / 100.0 * DT1) / 60.0
        Q = K * 100.0 * delta_T
        ilosc = math.ceil(Q / 4300)

        assert math.isclose(res.delta_T, delta_T, rel_tol=1e-12)
        assert math.isclose(res.Q, Q, rel_tol=1e-12)
        assert res.ilosc_zaworow == ilosc
        assert res.przeplyw_zaworu == 4300
        assert res.typ_zaworu == "Maxi Elebar"

    def test_evo_vertical_uzywa_swojej_wydajnosci(self):
        res = calculate_decompression_valves(
            V=100.0, temp_przed=20.0, temp_za=-30.0, F=2.0,
            typ_zaworu="Maxi Elebar EVO-VERTICAL",
        )
        assert res.przeplyw_zaworu == 1430
        assert res.typ_zaworu == "Maxi Elebar EVO-VERTICAL"

    def test_domyslny_typ_zaworu(self):
        res = calculate_decompression_valves(
            V=50.0, temp_przed=10.0, temp_za=-20.0, F=1.0,
        )
        assert res.typ_zaworu == "Maxi Elebar"
        assert res.przeplyw_zaworu == 4300

    def test_ilosc_zaworow_zaokraglana_w_gore(self):
        res = calculate_decompression_valves(
            V=1000.0, temp_przed=20.0, temp_za=-40.0, F=5.0,
        )
        # Liczba zaworów musi być liczbą całkowitą >= 1.
        assert isinstance(res.ilosc_zaworow, int)
        assert res.ilosc_zaworow >= 1
        assert res.ilosc_zaworow >= res.Q / res.przeplyw_zaworu

    def test_bez_posrednich_zaokraglen(self):
        # Q powinno wynikać bezpośrednio ze wzoru, bez zaokrąglania delta_T.
        res = calculate_decompression_valves(
            V=37.0, temp_przed=13.0, temp_za=-27.0, F=3.0,
        )
        delta_T = (3.0 / 37.0 * 40.0) / 60.0
        assert math.isclose(res.Q, K * 37.0 * delta_T, rel_tol=1e-12)


class TestValidation:
    @pytest.mark.parametrize("V", [0.0, -1.0, -100.0])
    def test_objetosc_niedodatnia(self, V):
        with pytest.raises(ValueError):
            calculate_decompression_valves(V=V, temp_przed=20.0, temp_za=-30.0, F=2.0)

    def test_objetosc_powyzej_limitu(self):
        with pytest.raises(ValueError):
            calculate_decompression_valves(
                V=V_MAX + 1, temp_przed=20.0, temp_za=-30.0, F=2.0
            )

    @pytest.mark.parametrize("F", [0.0, -1.0])
    def test_F_niedodatnie(self, F):
        with pytest.raises(ValueError):
            calculate_decompression_valves(V=100.0, temp_przed=20.0, temp_za=-30.0, F=F)

    def test_F_powyzej_limitu(self):
        with pytest.raises(ValueError):
            calculate_decompression_valves(
                V=100.0, temp_przed=20.0, temp_za=-30.0, F=F_MAX + 1
            )

    def test_temperatury_rowne(self):
        with pytest.raises(ValueError):
            calculate_decompression_valves(V=100.0, temp_przed=10.0, temp_za=10.0, F=2.0)

    def test_temp_przed_nizsza_niz_za(self):
        with pytest.raises(ValueError):
            calculate_decompression_valves(
                V=100.0, temp_przed=-30.0, temp_za=20.0, F=2.0
            )

    @pytest.mark.parametrize("temp", [TEMP_MIN - 1, TEMP_MAX + 1])
    def test_temperatura_poza_zakresem(self, temp):
        with pytest.raises(ValueError):
            calculate_decompression_valves(
                V=100.0, temp_przed=temp, temp_za=TEMP_MIN - 5, F=2.0
            )

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_wartosci_niefinitne(self, bad):
        with pytest.raises(ValueError):
            calculate_decompression_valves(V=bad, temp_przed=20.0, temp_za=-30.0, F=2.0)

    def test_nieznany_typ_zaworu(self):
        with pytest.raises(KeyError):
            calculate_decompression_valves(
                V=100.0, temp_przed=20.0, temp_za=-30.0, F=2.0,
                typ_zaworu="Nieistniejący Zawór",
            )


class TestValveResults:
    def test_dataclass_jest_niemutowalny(self):
        res = calculate_decompression_valves(
            V=100.0, temp_przed=20.0, temp_za=-30.0, F=2.0
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            res.ilosc_zaworow = 999  # type: ignore[misc]

    def test_dostepne_typy_zaworow(self):
        assert "Maxi Elebar" in ZAWORY
        assert "Maxi Elebar EVO-VERTICAL" in ZAWORY
        assert ZAWORY["Maxi Elebar"] == 4300
        assert ZAWORY["Maxi Elebar EVO-VERTICAL"] == 1430
