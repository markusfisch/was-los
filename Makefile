SCRIPT = update
HTML = was.html

$(HTML): $(SCRIPT)
	./$(SCRIPT) > $@

up: $(HTML)
	scp $(HTML) hhsw.de@ssh.strato.de:

format:
	pep8ify -n -w -f maximum_line_length $(SCRIPT)

clean:
	rm -f $(HTML)
