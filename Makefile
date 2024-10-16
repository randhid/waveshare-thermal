module.tar.gz: requirements.txt src/*.py meta.json
	rm -f $@
	tar czf $@ $^
