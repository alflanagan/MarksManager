PIP_COMPILE = pip-compile --generate-hashes --allow-unsafe --resolver=backtracking

requirements:
	$(PIP_COMPILE) requirements.in; $(PIP_COMPILE) requirements.dev.in

upgrade-requirements:
	$(PIP_COMPILE) --upgrade requirements.in; $(PIP_COMPILE) --upgrade requirements.dev.in

sync:
	pip-sync requirements.txt requirements.dev.txt
