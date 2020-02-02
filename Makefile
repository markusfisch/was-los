HTDOCS = htdocs

update:
	./bin/update_events.py $(HTDOCS)

format:
	pep8ify -n -w -f maximum_line_length bin/*.py

clean:
	rm -f $(HTDOCS)/*.html
