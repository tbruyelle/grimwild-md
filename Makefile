.PHONY: test webapp venv venv-activate

HEROKU_APP=grimwild-md

venv:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

test:
	python3 -m unittest discover tests

webapp:
	uvicorn app:app --reload

deploy:
	heroku container:login
	heroku container:push web --app $(HEROKU_APP)
	heroku container:release web --app $(HEROKU_APP)
