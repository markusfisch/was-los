HTDOCS = htdocs

html: clean
	./bin/update_events.py $(HTDOCS) res/screen.css

install:
	scp bin/update_events.py m9h@menkent.uberspace.de:bin/
	scp htdocs/*.js* htdocs/*.png htdocs/.htaccess \
		m9h@menkent.uberspace.de:html/

format:
	pep8ify -n -w -f maximum_line_length bin/*.py

clean:
	rm -f $(HTDOCS)/*.html
