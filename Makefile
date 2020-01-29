SCRIPT = update

fetch:
	./$(SCRIPT)

up:
	scp *.html hhsw.de@ssh.strato.de:

format:
	pep8ify -n -w -f maximum_line_length $(SCRIPT)

clean:
	rm -f *.html
