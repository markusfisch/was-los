HTDOCS = htdocs

update:
	./bin/update_events.py $(HTDOCS)

install:
	scp bin/update_events.py m9h@menkent.uberspace.de:bin/
	scp htdocs/*.js* htdocs/*.css htdocs/*.png htdocs/.htaccess \
		m9h@menkent.uberspace.de:html/

format:
	pep8ify -n -w -f maximum_line_length bin/*.py

clean:
	rm -f $(HTDOCS)/*.html
