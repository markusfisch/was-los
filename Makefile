GENERATOR = ./src/update_events.py
HTDOCS = htdocs
SERVER = m9h@francisco.uberspace.de

html: clean
	$(GENERATOR) $(HTDOCS) res/screen.css

install:
	scp $(GENERATOR) $(SERVER):bin/
	scp $(HTDOCS)/*.js* $(HTDOCS)/*.png $(HTDOCS)/.htaccess \
		$(SERVER):html/
	scp res/screen.css $(SERVER):res/screen.css

format:
	pep8ify -n -w -f all -f maximum_line_length src/*.py

clean:
	rm -f $(HTDOCS)/*.html
