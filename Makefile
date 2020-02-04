GENERATOR = ./bin/update_events.py
HTDOCS = htdocs
SERVER = m9h@menkent.uberspace.de

html: clean
	$(GENERATOR) $(HTDOCS) res/screen.css

install:
	scp $(GENERATOR) $(SERVER):bin/
	scp $(HTDOCS)/*.js* $(HTDOCS)/*.png $(HTDOCS)/.htaccess \
		$(SERVER):html/

format:
	pep8ify -n -w -f maximum_line_length bin/*.py

clean:
	rm -f $(HTDOCS)/*.html
