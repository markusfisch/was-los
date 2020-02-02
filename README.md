# Was machen?

Simple, searchable list of what to do around Nuremberg, Germany.

## Requirements

The following packages need to be installed to generate the static HTML pages:

	$ pip3 install untangle requests

## Generation

There's a Python script that's supposed to run on midnight that will generate
a couple of static HTML pages in the given directory:

	$ ./bin/update_events.py htdocs
