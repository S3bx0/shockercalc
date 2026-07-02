from tpof.core.calculations import calculate_freezing
from tpof.core.formatters import format_results_text
from tpof.core.models import FreezingInputs, Product


def _results():
    product = Product(
        nazwa="Produkt chroniony",
        kategoria="test",
        c1=3.47,
        c2=2.22,
        T_zam=-2.0,
        wodaprocent=68.26,
        L1=223.0,
    )
    inputs = FreezingInputs(
        masa_kg=100.0,
        T_pocz_C=5.0,
        T_konc_C=-18.0,
        czas_h=24.0,
    )
    return calculate_freezing(inputs, product)


def test_mobile_report_hides_source_product_properties():
    text = format_results_text(_results(), include_product_properties=False)

    assert "Nazwa produktu: Produkt chroniony" in text
    assert "Suma mocy potrzebnej" in text
    assert "Ciepło właściwe" not in text
    assert "Zawartość wody" not in text
    assert "Ciepło topnienia" not in text
    assert "Temperatura początkowego zamarzania" not in text


def test_desktop_report_keeps_product_properties_by_default():
    text = format_results_text(_results())

    assert "Ciepło właściwe powyżej zamrażania" in text
    assert "Zawartość wody" in text
    assert "Ciepło topnienia" in text


def test_estimated_freezing_point_text_does_not_claim_zero_fallback():
    product = Product(
        nazwa="Bez katalogowego T_zam",
        kategoria="test",
        c1=3.4,
        c2=1.9,
        T_zam=None,
        wodaprocent=50.0,
        L1=220.0,
    )
    results = calculate_freezing(
        FreezingInputs(masa_kg=10.0, T_pocz_C=5.0, T_konc_C=-18.0, czas_h=8.0),
        product,
    )

    text = format_results_text(results)

    assert "szacunkowo — brak danych katalogowych" in text
    assert "przyjęto 0°C" not in text
    assert "Temperatura początkowego zamarzania [°C]: -1.20" in text
