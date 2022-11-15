install: build clean

clean:
	rm -f -r build/
	rm -f -r dist/
	rm -f -r *.egg-info
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f  {} +
	find . -name '__pycache__' -exec rm -rf  {} +

rebuild: clean
	python setup.py install

publish: clean
	python setup.py sdist bdist_wheel
	python -m twine upload dist/*

build: clean
	python setup.py install