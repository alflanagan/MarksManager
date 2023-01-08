requirements:
	pip-compile --generate-hashes --allow-unsafe requirements.in; \
	pip-compile --generate-hashes --allow-unsafe requirements.dev.in

sync:
	pip-sync requirements.txt requirements.dev.txt
