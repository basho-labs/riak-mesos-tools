all: test packages docs

clean:
	scripts/clean.sh

env:
	scripts/env.sh

test: env
	scripts/test.sh

packages: env
	scripts/packages.sh

docs:
	cat README.md | pandoc --from markdown_github --to rst > README.rst
