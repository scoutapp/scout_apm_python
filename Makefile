clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +

clean-cache:
	find . -name '__pycache__' -exec rm -rf {} +
	rm -rf .pytest_cache

clean-build:
	rm -rf build/
	rm -rf dist/
	find . -name '*.egg-info' -exec rm -rf {} +

clean: clean-pyc clean-cache clean-build

style:
	black src tests setup.py
	isort --recursive src tests setup.py

lint:
	tox -e check

test: clean-pyc
	tox -v --workdir /tmp/tox

test-pyenv:
	pyenv local `cat .python-version | xargs` && tox -v --workdir /tmp/tox
