# Was machen?

Simple, searchable list of what to do around Nuremberg, Germany.

## Requirements

The following packages need to be installed to generate the static HTML pages:

	$ pip3 install untangle requests

## Generation

There's a Python script that's supposed to run on midnight that will generate
a couple of static HTML pages in the given directory (and the given style
sheet):

	$ ./bin/update_events.py htdocs res/screen.css

The style sheet is embedded because it is quite small and it will avoid the
display of unstyled content when on a bad connection.

If you've got `make`, you can simply run:

	$ make
