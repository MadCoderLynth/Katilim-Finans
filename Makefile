.PHONY: kur test dogrula panel temiz

kur:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	python3 tests/test_motor.py

# make dogrula DOSYA=veri/ham/THYAO_2025_yillik.html
dogrula:
	python3 -m katilim.cli dogrula $(DOSYA)

panel:
	python3 -m katilim.cli toplu veri/ham --csv veri/panel/uygunluk_paneli.csv

temiz:
	find . -name __pycache__ -type d -exec rm -rf {} +
