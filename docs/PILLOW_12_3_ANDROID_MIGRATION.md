# Migracja Pillow 12.3.0 na Androidzie

## Cel

Zastąpić Pillow 11.3.0 w rzeczywistym APK/AAB wydaniem 12.3.0 bez zmiany
zachowania aplikacji, wzrostu powierzchni ataku ani przypadkowego linkowania
bibliotek z hosta CI.

## Punkt odniesienia

- `python-for-android`: commit
  `58d21141f17c889bf8585f5665921d72028f8831`;
- poprzednia receptura: Pillow 11.3.0;
- bazowy podpisany AAB: 48 205 179 B, tylko `arm64-v8a`, 15 bibliotek;
- kontrola wyrównania bibliotek: 16 KB — zaliczona;
- Pillow w bazowym `libpybundle.so`: `pillow-11.3.0.dist-info`, `_imaging.so`
  i `_imagingft.so`, bez `_webp.so`.

WebP używane przez katalog produktów jest renderowane przez Kivy/SDL2.
Receptura nie dodaje `libwebp` do Pillow, dzięki czemu zachowujemy możliwości
poprzedniego AAB i nie zwiększamy paczki drugim dekoderem bez potrzeby.

## Kontrolowana receptura

Receptura w `p4a-recipes/pillow` jest małą kopią receptury z przypiętego p4a,
z następującymi zmianami:

- Pillow 12.3.0 z oficjalnego sdist PyPI;
- SHA-256:
  `3b8182a766685eaa002637e28b4ec8d6b18819a0c71f579bf0dbaa5830297cce`;
- konfiguracja PEP 517 `platform-guessing=disable`;
- wyłączony hostowy `pkg-config`;
- jawne pary `lib:include` dla JPEG, FreeType, HarfBuzz i zlib z NDK;
- minimalna łatka usuwająca ścieżki `sys.prefix` hosta.

## Bramy automatyczne

- pełna suita testów i pokrycie co najmniej 50%;
- Ruff i mypy;
- `pip-audit` bez wyjątków dla mobilnego Pillow;
- receptura i źródło przypięte wersją oraz SHA-256;
- `verify_android_python_packages.py` wymaga dokładnie Pillow 12.3.0,
  `_imaging.so` i `_imagingft.so` w finalnym APK/AAB;
- dotychczasowe bramy ABI, uprawnień, backupu, sieci, Firebase, podpisu,
  Bundletool i wyrównania 16 KB.

## Smoke na Androidzie

Po zielonym buildzie należy na fizycznym urządzeniu ARM sprawdzić:

1. start aplikacji i otwarcie katalogu produktów WebP;
2. obrazy PNG z alpha oraz skalowanie grafik;
3. odczyt JPEG i korektę orientacji EXIF;
4. wygenerowanie i otwarcie raportu PDF;
5. porównanie rozmiaru oraz czasu startu z bazowym AAB.

Własną recepturę można usunąć dopiero wtedy, gdy przypięty upstream
`python-for-android` dostarczy równoważną, zweryfikowaną wersję.
