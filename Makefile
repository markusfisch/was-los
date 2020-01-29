SCRIPT = update
HTML = what-to-do.html

$(HTML):
	./$(SCRIPT) > $@

up: $(HTML)
	scp $(HTML) hhsw.de@ssh.strato.de:

format:
	pep8ify -n -w $(SCRIPT)

clean:
	rm -f $(HTML)
