"""Testy obliczeń termodynamicznych."""

import math

import pytest

from tpof.core.calculations import _estimate_T_zam, calculate_freezing
from tpof.core.models import FreezingInputs, Product


@pytest.fixture
def szynka() -> Product:
    """Realny przykład z bazy: szynka wieprzowa, cała, chuda."""
    return Product(
        nazwa="Szynka wieprzowa",
        c1=3.47,
        c2=2.22,
        T_zam=-2.0,
        wodaprocent=68.26,
        L1=223.0,
    )


@pytest.fixture
def mrozona() -> Product:
    """Produkt bez punktu zamarzania (T_zam=None)."""
    return Product(nazwa="Tajemnicza ryba", c1=3.5, c2=1.8, T_zam=None, L1=200.0)


class TestCalculateFreezing:
    def test_pelny_cykl_chlodzenie_zamrozenie_domrozenie(self, szynka):
        inputs = FreezingInputs(masa_kg=100.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=24.0)
        res = calculate_freezing(inputs, szynka)

        # Schładzanie: 100 * 3.47 * (5 - (-2)) = 2429 kJ
        assert math.isclose(res.Q_schladzanie_kJ, 2429.0, rel_tol=1e-9)
        # Zamrożenie: 100 * 223 = 22300 kJ
        assert math.isclose(res.Q_zamrozenie_kJ, 22300.0, rel_tol=1e-9)
        # Domrożenie: 100 * 2.22 * (-2 - (-18)) = 3552 kJ
        assert math.isclose(res.Q_domrozenie_kJ, 3552.0, rel_tol=1e-9)

        # Moc całkowita = suma_Q / (t*3600)
        expected_P = (2429 + 22300 + 3552) / (24 * 3600)
        assert math.isclose(res.P_total_kW, expected_P, rel_tol=1e-9)

    def test_tylko_schladzanie_powyzej_zamrazania(self, szynka):
        inputs = FreezingInputs(masa_kg=50.0, T_pocz_C=20.0, T_konc_C=4.0, czas_h=10.0)
        res = calculate_freezing(inputs, szynka)

        # Tylko c1 * (20 - 4) — nie powinno być zamrażania ani domrażania.
        assert math.isclose(res.Q_schladzanie_kJ, 50 * 3.47 * 16, rel_tol=1e-9)
        assert res.Q_zamrozenie_kJ == 0.0
        assert res.Q_domrozenie_kJ == 0.0

    def test_produkt_bez_punktu_zamarzania_szacuje_z_wody(self, mrozona):
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-10.0, czas_h=5.0)
        res = calculate_freezing(inputs, mrozona)

        assert res.T_zam_szacunkowy is True
        # mrozona ma wodaprocent=None -> fallback -0.6
        assert res.T_zam_uzyte_C == -0.6

    def test_produkt_juz_zamrozony_tylko_domrazanie(self, szynka):
        inputs = FreezingInputs(masa_kg=20.0, T_pocz_C=-5.0, T_konc_C=-25.0, czas_h=12.0)
        res = calculate_freezing(inputs, szynka)

        assert res.Q_schladzanie_kJ == 0.0
        assert res.Q_zamrozenie_kJ == 0.0
        # T_pocz < T_zam (-5 < -2) -> tylko domrażanie c2*(T_pocz - T_konc) = 20*2.22*20
        assert math.isclose(res.Q_domrozenie_kJ, 20 * 2.22 * 20, rel_tol=1e-9)

    def test_zerowy_czas_rzuca_wyjatek(self, szynka):
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=0.0)
        with pytest.raises(ValueError, match="Czas pracy musi być > 0"):
            calculate_freezing(inputs, szynka)

    def test_brak_c1_nie_powoduje_bledu(self):
        product = Product(nazwa="Niekompletny", c1=None, c2=2.0, T_zam=-1.0, L1=200.0)
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-10.0, czas_h=5.0)
        res = calculate_freezing(inputs, product)

        assert res.Q_schladzanie_kJ == 0.0  # brak c1 -> 0, nie wyjątek
        assert res.Q_zamrozenie_kJ == 10 * 200
        assert math.isclose(res.Q_domrozenie_kJ, 10 * 2.0 * 9, rel_tol=1e-9)


class TestEdgeCases:
    """Przypadki brzegowe i degeneracja danych."""

    def test_T_konc_rowne_T_zam_liczy_pelne_zamrozenie(self, szynka):
        """Gdy zatrzymujemy się dokładnie na punkcie zamarzania, ciepło utajone
        jest liczone w całości, a domrażanie = 0."""
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-2.0, czas_h=5.0)
        res = calculate_freezing(inputs, szynka)
        assert math.isclose(res.Q_schladzanie_kJ, 10 * 3.47 * 7, rel_tol=1e-9)
        assert math.isclose(res.Q_zamrozenie_kJ, 10 * 223, rel_tol=1e-9)
        assert res.Q_domrozenie_kJ == 0.0

    def test_T_pocz_rowne_T_zam_traktowane_jak_zamrozony(self, szynka):
        """Gdy startujemy z punktu zamarzania, kod wchodzi w gałąź 'już zamrożony'."""
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=-2.0, T_konc_C=-18.0, czas_h=5.0)
        res = calculate_freezing(inputs, szynka)
        assert res.Q_schladzanie_kJ == 0.0
        assert res.Q_zamrozenie_kJ == 0.0
        assert math.isclose(res.Q_domrozenie_kJ, 10 * 2.22 * 16, rel_tol=1e-9)

    def test_T_pocz_rowne_T_konc_jest_odrzucane(self, szynka):
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=-5.0, T_konc_C=-5.0, czas_h=5.0)
        with pytest.raises(ValueError, match="Temperatura końcowa musi być niższa"):
            calculate_freezing(inputs, szynka)

    def test_T_konc_wyzsza_od_T_pocz_jest_odrzucana(self, szynka):
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=-10.0, T_konc_C=-5.0, czas_h=5.0)
        with pytest.raises(ValueError, match="Temperatura końcowa musi być niższa"):
            calculate_freezing(inputs, szynka)

    def test_brak_L1_pomija_ciepło_utajone(self):
        """Gdy brak ciepła topnienia, etap zamrażania = 0, ale c2 nadal działa."""
        product = Product(nazwa="BezL1", c1=3.0, c2=2.0, T_zam=-1.0, L1=None)
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-10.0, czas_h=5.0)
        res = calculate_freezing(inputs, product)
        assert math.isclose(res.Q_schladzanie_kJ, 10 * 3.0 * 6, rel_tol=1e-9)
        assert res.Q_zamrozenie_kJ == 0.0
        assert math.isclose(res.Q_domrozenie_kJ, 10 * 2.0 * 9, rel_tol=1e-9)

    def test_brak_c2_pomija_domrazanie(self):
        product = Product(nazwa="BezC2", c1=3.0, c2=None, T_zam=-1.0, L1=200.0)
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-10.0, czas_h=5.0)
        res = calculate_freezing(inputs, product)
        assert math.isclose(res.Q_schladzanie_kJ, 10 * 3.0 * 6, rel_tol=1e-9)
        assert math.isclose(res.Q_zamrozenie_kJ, 10 * 200, rel_tol=1e-9)
        assert res.Q_domrozenie_kJ == 0.0

    def test_wszystkie_dane_zerowe_lub_None(self):
        product = Product(nazwa="Pusty", c1=None, c2=None, T_zam=None, L1=None)
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-10.0, czas_h=5.0)
        res = calculate_freezing(inputs, product)
        assert res.Q_total_kJ == 0.0
        assert res.T_zam_szacunkowy is True
        assert res.T_zam_uzyte_C == -0.6  # fallback bez wody

    def test_masa_zero(self, szynka):
        inputs = FreezingInputs(masa_kg=0.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=5.0)
        res = calculate_freezing(inputs, szynka)
        assert res.Q_total_kJ == 0.0
        assert res.P_total_kW == 0.0

    def test_ujemny_czas_rzuca_wyjatek(self, szynka):
        inputs = FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=-1.0)
        with pytest.raises(ValueError):
            calculate_freezing(inputs, szynka)


class TestSkalowalnoscIProporcje:
    """Sprawdza, że wynik skaluje się liniowo z masą i odwrotnie do czasu."""

    def test_podwojna_masa_podwojna_energia(self, szynka):
        i1 = FreezingInputs(masa_kg=100.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=10.0)
        i2 = FreezingInputs(masa_kg=200.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=10.0)
        r1 = calculate_freezing(i1, szynka)
        r2 = calculate_freezing(i2, szynka)
        assert math.isclose(r2.Q_total_kJ, 2 * r1.Q_total_kJ, rel_tol=1e-9)
        assert math.isclose(r2.P_total_kW, 2 * r1.P_total_kW, rel_tol=1e-9)

    def test_podwojny_czas_polowa_mocy(self, szynka):
        i1 = FreezingInputs(masa_kg=100.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=10.0)
        i2 = FreezingInputs(masa_kg=100.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=20.0)
        r1 = calculate_freezing(i1, szynka)
        r2 = calculate_freezing(i2, szynka)
        assert math.isclose(r1.Q_total_kJ, r2.Q_total_kJ, rel_tol=1e-9)
        assert math.isclose(r2.P_total_kW, r1.P_total_kW / 2, rel_tol=1e-9)

    def test_suma_etapow_rowna_Q_total(self, szynka):
        inputs = FreezingInputs(masa_kg=123.45, T_pocz_C=18.0, T_konc_C=-25.0, czas_h=14.5)
        res = calculate_freezing(inputs, szynka)
        suma = res.Q_schladzanie_kJ + res.Q_zamrozenie_kJ + res.Q_domrozenie_kJ
        assert math.isclose(res.Q_total_kJ, suma, rel_tol=1e-12)
        suma_P = res.P_schladzanie_kW + res.P_zamrozenie_kW + res.P_domrozenie_kW
        assert math.isclose(res.P_total_kW, suma_P, rel_tol=1e-12)


class TestJednostekIKonwersji:
    """Sprawdza fizyczną poprawność jednostek (kJ/kW, sekundy/godziny)."""

    def test_konwersja_kJ_na_kW_zgodna_z_definicja(self, szynka):
        """P[kW] = Q[kJ] / (t[h] * 3600). Sprawdzenie ręczne na 1h."""
        inputs = FreezingInputs(masa_kg=1.0, T_pocz_C=10.0, T_konc_C=10.0 - 1.0, czas_h=1.0)
        # Tylko schładzanie, ΔT=1, m=1 -> Q = c1 [kJ]
        res = calculate_freezing(inputs, szynka)
        assert math.isclose(res.Q_schladzanie_kJ, szynka.c1, rel_tol=1e-9)
        # Moc = c1 [kJ] / 3600s = c1/3600 [kW]
        assert math.isclose(res.P_schladzanie_kW, szynka.c1 / 3600.0, rel_tol=1e-9)

    def test_godzina_versus_doba_24x_mniejsza_moc(self, szynka):
        i_1h = FreezingInputs(masa_kg=100.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=1.0)
        i_24h = FreezingInputs(masa_kg=100.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=24.0)
        r1 = calculate_freezing(i_1h, szynka)
        r24 = calculate_freezing(i_24h, szynka)
        assert math.isclose(r1.P_total_kW, 24 * r24.P_total_kW, rel_tol=1e-9)


@pytest.mark.parametrize("masa,T_p,T_k,t,exp_Q,exp_P", [
    # (kg, °C pocz, °C konc, h, oczekiwana Q [kJ], oczekiwana P [kW])
    # Szynka c1=3.47 c2=2.22 T_zam=-2 L1=223
    # Tylko schładzanie 100kg, 10->5°C w 1h: Q = 100*3.47*5 = 1735, P=1735/3600
    (100.0, 10.0, 5.0, 1.0, 100 * 3.47 * 5, (100 * 3.47 * 5) / 3600.0),
    # Pełny cykl 1kg, 0->-10°C w 1h:
    # Q_schl = 1*3.47*2 = 6.94; Q_zam = 1*223 = 223; Q_dom = 1*2.22*8 = 17.76
    # Σ = 247.7; P = 247.7/3600
    (1.0, 0.0, -10.0, 1.0, 1 * 3.47 * 2 + 1 * 223 + 1 * 2.22 * 8,
     (1 * 3.47 * 2 + 1 * 223 + 1 * 2.22 * 8) / 3600.0),
])
def test_parametryzowane_realne_przypadki(szynka, masa, T_p, T_k, t, exp_Q, exp_P):
    inputs = FreezingInputs(masa_kg=masa, T_pocz_C=T_p, T_konc_C=T_k, czas_h=t)
    res = calculate_freezing(inputs, szynka)
    assert math.isclose(res.Q_total_kJ, exp_Q, rel_tol=1e-9)
    assert math.isclose(res.P_total_kW, exp_P, rel_tol=1e-9)


class TestProperties:
    """Właściwości matematyczne wyniku."""

    def test_wszystkie_Q_nieujemne(self, szynka):
        inputs = FreezingInputs(masa_kg=100.0, T_pocz_C=20.0, T_konc_C=-30.0, czas_h=8.0)
        res = calculate_freezing(inputs, szynka)
        assert res.Q_schladzanie_kJ >= 0
        assert res.Q_zamrozenie_kJ >= 0
        assert res.Q_domrozenie_kJ >= 0
        assert res.P_total_kW >= 0

    def test_wieksza_roznica_temp_wieksze_Q(self, szynka):
        i1 = FreezingInputs(masa_kg=100.0, T_pocz_C=10.0, T_konc_C=-10.0, czas_h=10.0)
        i2 = FreezingInputs(masa_kg=100.0, T_pocz_C=10.0, T_konc_C=-30.0, czas_h=10.0)
        r1 = calculate_freezing(i1, szynka)
        r2 = calculate_freezing(i2, szynka)
        assert r2.Q_total_kJ > r1.Q_total_kJ
        # Różnica wynika tylko z dodatkowego domrażania o ΔT=20K
        assert math.isclose(
            r2.Q_domrozenie_kJ - r1.Q_domrozenie_kJ,
            100 * szynka.c2 * 20,
            rel_tol=1e-9,
        )



class TestEstimateTzam:
    """Szacowanie punktu zamarzania ze wzoru."""

    def test_brak_wody_zwraca_fallback(self):
        assert _estimate_T_zam(None) == -0.6
        assert _estimate_T_zam(0) == -0.6

    def test_woda_100_procent_okolo_06(self):
        # 100% wody -> -0.6 * (100/100) = -0.6
        assert _estimate_T_zam(100.0) == -0.6

    def test_woda_50_procent_okolo_12(self):
        assert _estimate_T_zam(50.0) == -1.2

    def test_monotoniczne_malenie_z_wody(self):
        # Mniej wody -> niższy (bardziej ujemny) punkt zamarzania
        assert _estimate_T_zam(80.0) > _estimate_T_zam(50.0) > _estimate_T_zam(20.0)
