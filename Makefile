.PHONY: dist distclean

dist:
	zip -r bidpazari.zip -x \*__pycache__\* -x \*.pyc -x \*.iml -@ < .zipfile

distclean:
	rm -f bidpazari.zip
