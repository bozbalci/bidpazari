dist:
	zip -r bidpazari.zip . \
		-x Makefile \
		-x \*tools/\* \
		-x .\* \
		-x \*__pycache__\* \
		-x \*.sqlite3 \
		-x \*.pyc \

distclean:
	rm -f bidpazari.zip
