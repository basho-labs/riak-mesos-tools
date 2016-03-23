BASEDIR ?= $(PWD)

all: test packages
dev: activate-env test packages

clean:
	rm -rf $(BASEDIR)/.tox $(BASEDIR)/env $(BASEDIR)/build $(BASEDIR)/dist
	echo "Deleted virtualenv and test artifacts."

env:
	virtualenv -q $(BASEDIR)/env --prompt='(riak-mesos) '
	echo "Virtualenv created."

activate-env: env
	source $(BASEDIR)/env/bin/activate
	echo "Virtualenv activated."

deps:
	pip install -r $(BASEDIR)/requirements.txt
	pip install -e $(BASEDIR)
	echo "Requirements installed."

test: deps
	tox -e py27-integration

test-end-to-end: deps
	tox -e py27-end-to-end

packages: deps
	python setup.py bdist_wheel
	python setup.py sdist

docs:
	cat README.md | pandoc --from markdown_github --to rst > README.rst
