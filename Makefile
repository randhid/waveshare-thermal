module.tar.gz: requirements.txt src/*.py meta.json run.sh
	rm -f $@
	tar czf $@ $^
