# Was machen?

<img src="htdocs/icon_192.png" alt="Icon" width="128"/>

Simple, searchable list of what to do around Nuremberg, Germany.

## Rationale

Because I think it's far too cumbersome to get an overview of what I can do
in my free time. I just want to check _one_ list instead of multiple web
sites. Especially because some of them don't perform very well (I'm looking
at you, [cinecitta.de](https://www.cinecitta.de)).

Others are quite helpful in their departement but lack content I am
interested in. [Mehrwert Zone](https://mwz.mobi/), for example, gives a
similar listing and even offers a location based search, but is lacking
movie screenings.

Finally, I want this list to be as accessible as possible because I like
to check my options when I'm out and about. So it should also load as fast
as possible, even on a bad connection.

## Requirements

The following packages need to be installed to generate the static HTML pages:

	$ pip3 install lxml requests

## Generation

There's a Python script that's supposed to run around midnight that will
generate a couple of static HTML pages:

	$ ./bin/update_events.py htdocs res/screen.css

The first argument (`htdocs`) is the output directory.

The second argument (`res/screen.css`) is the stylesheet to embed in the
static HTML pages. The stylesheet is embedded because it is quite small and
embedding it keeps browsers from showing unstyled content when on a bad
connection.

In this repo, you can simply run `make` to generate the HTML files:

	$ make

Now, you just need to put `htdocs` on a web server.

## Content sources

Currently aggregates events and movie screenings from:

* [Veranstaltungskalender für Nürnberg, Fürth, Erlangen und Schwabach](https://meineveranstaltungen.nuernberg.de)
* [Kino.de](https://www.kino.de/)
* [Cinecitta Nürnberg](https://www.cinecitta.de/)

All content is property of those sources.
