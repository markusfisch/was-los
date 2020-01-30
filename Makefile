HTDOCS = htdocs
DATA = events.json
WEBROOT = hhsw.de@ssh.strato.de:sites/wasmachen
OPTIONS = \
	--recursive \
	--links \
	--update \
	--delete-after \
	--times \
	--compress

live: $(DATA)
	rsync $(OPTIONS) $(HTDOCS)/* $(WEBROOT)

$(DATA):
	./fetch_events.py

format:
	pep8ify -n -w -f maximum_line_length *.py

clean:
	rm -f $(DATA)
