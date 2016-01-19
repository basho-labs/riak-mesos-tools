all: env test packages docs

clean:
	scripts/clean.sh

env:
	scripts/env.sh

test:
	scripts/test.sh

packages:
	scripts/packages.sh

docs:
	cat README.md | pandoc --from markdown_github --to rst > README.rst
