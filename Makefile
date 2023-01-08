PIP_COMPILE = pip-compile --generate-hashes --allow-unsafe --resolver=backtracking

requirements:
	$(PIP_COMPILE) requirements.in; $(PIP_COMPILE) requirements.dev.in

sync:
	pip-sync requirements.txt requirements.dev.txt
