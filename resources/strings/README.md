Refrigeration Calc mobile localization scaffold
==============================================

Runtime strings are currently served from `tpof/mobile/main.py` because the
Kivy mobile UI is Python-first. This directory reserves language resource
files for the next localization pass and mirrors the planned Google Play
languages without affecting the Android build.

Current behavior:
- `pl` and `en` are implemented in the runtime dictionary.
- `es`, `fr`, `it`, `pt`, `ja`, and `zh` fall back to English until reviewed
  translations are added.

TODO: Move runtime UI strings from the Python dictionary into these resource
files after the translation workflow is finalized.
