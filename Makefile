.PHONY: test webapp venv venv-activate

venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

test:
	python3 -m unittest discover tests

webapp:
	uvicorn app:app --reload
