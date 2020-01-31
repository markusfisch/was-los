HTDOCS = htdocs
WEBROOT = hhsw.de@ssh.strato.de:sites/wasmachen
OPTIONS = \
	--recursive \
	--links \
	--update \
	--delete-after \
	--times \
	--compress

live: update
	rsync $(OPTIONS) $(HTDOCS)/* $(WEBROOT)

update:
	./bin/update_events.py $(HTDOCS)

format:
	pep8ify -n -w -f maximum_line_length *.py

clean:
	rm -f $(HTDOCS)/*.html
