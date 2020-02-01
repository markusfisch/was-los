#!/usr/bin/env python3

import json
import untangle
import requests
import sys

from datetime import datetime, timedelta


def add_event(events, from_time, to_time, template, day, begin, end):
    if begin == "":
        begin = '00:00'
    begin = day + ' ' + begin
    if end == "":
        end = '23:59'
    end = day + ' ' + end
    begin_date = datetime.strptime(begin, '%Y-%m-%d %H:%M')
    if begin_date < from_time or begin_date > to_time:
        return
    template['begin'] = begin
    template['end'] = end
    events.append(template.copy())


def parse_events_nuernberg(events, from_time, to_time, xml):
    def collect_days(begin, end, weekday):
        # map german weekday abbreviations to datetime.weekday()
        if weekday == 'mo':
            weekday = 0
        elif weekday == 'di':
            weekday = 1
        elif weekday == 'mi':
            weekday = 2
        elif weekday == 'do':
            weekday = 3
        elif weekday == 'fr':
            weekday = 4
        elif weekday == 'sa':
            weekday = 5
        elif weekday == 'so':
            weekday = 6
        else:
            return []
        dt = datetime.strptime(begin, '%Y-%m-%d')
        until = datetime.strptime(end, '%Y-%m-%d')
        days = []
        while dt <= until:
            if dt.weekday() == weekday:
                days.append(dt.strftime('%Y-%m-%d'))
            dt += timedelta(days=1)
        return days

    #       .-"-.
    #     _/_-.-_\_
    #    / __} {__ \
    #   / //  "  \\ \
    #  / / \'---'/ \ \
    #  \ \_/`"""`\_/ /
    #   \           /
    # see https://meineveranstaltungen.nuernberg.de/Export_Schnittstelle.pdf
    for event in xml.ERGEBNIS.VERANSTALTUNG:
        elements_in_event = dir(event)
        template = {
            'name': event.TITEL.cdata,
            'place': event.ORT.cdata,
            'image_url': event.BILD.cdata if
                'BILD' in elements_in_event else '#',
            'url': event.DETAILLINK.cdata if
                'DETAILLINK' in elements_in_event else '#',
        }
        # add an event for all opening hours
        hours = event.OEFFNUNGSZEITEN
        elements_in_hours = dir(hours)
        t = hours['TYP']
        if t == '1':
            d = hours.DATUM
            add_event(
                events,
                from_time,
                to_time,
                template,
                d.cdata,
                d['BEGINN'],
                d['ENDE'],
            )
        elif t == '2' or 'DATUM' in elements_in_hours:
            for d in hours.DATUM:
                add_event(
                    events,
                    from_time,
                    to_time,
                    template,
                    d.cdata,
                    d['BEGINN'],
                    d['ENDE'],
                )
        elif t == '3' or 'OFFENETAGE' in elements_in_hours:
            days = {}
            # add all weekdays between DATUM1 and DATUM2
            begin = hours.DATUM1.cdata
            end = hours.DATUM2.cdata
            if 'OFFENETAGE' in elements_in_hours:
                for d in hours.OFFENETAGE.OFFENERTAG:
                    for day in collect_days(begin, end, d.cdata):
                        days[day] = {
                            'begin': d['BEGINN'],
                            'end': d['ENDE'],
                        }
            # remove exceptions
            if 'AUSNAHMEN' in elements_in_hours:
                for day in filter(None, hours.AUSNAHMEN.cdata.split(';')):
                    days.pop(day, None)
            # overwrite with deviating days
            if ('ABWEICHENDETAGE' in elements_in_hours and
                'ABWEICHENDERTAG' in dir(hours.ABWEICHENDETAGE)):
                for d in hours.ABWEICHENDETAGE.ABWEICHENDERTAG:
                    days[d.cdata] = {
                        'begin': d['BEGINN'],
                        'end': d['ENDE'],
                    }
            for day, times in days.items():
                add_event(
                    events,
                    from_time,
                    to_time,
                    template,
                    day,
                    times['begin'],
                    times['end'],
                )


def parse_cinecitta(events, from_time, to_time, shows):
    for item in shows['daten']['items']:
        template = {
            'name': item['film_titel'],
            'image_url': item['film_cover_src'],
            'url': 'https://www.cinecitta.de/' + item['filminfo_href'],
        }
        for theater in item['theater']:
            for screen in theater['leinwaende']:
                place = '%s %s' % (
                    screen['theater_name'],
                    screen['leinwand_name'],
                )
                template['place'] = place
                for showing in screen['vorstellungen']:
                    dt = datetime.fromisoformat(showing['datum_uhrzeit_iso'])
                    add_event(
                        events,
                        from_time,
                        to_time,
                        template,
                        dt.strftime('%Y-%m-%d'),
                        dt.strftime('%H:%M'),
                        (dt + timedelta(hours=2)).strftime('%H:%M'),
                    )


def fetch_events(from_time, to_time):
    events = []
    parse_events_nuernberg(events, from_time, to_time, untangle.parse(
        'http://meine-veranstaltungen.net/export.php5'
    ))
    parse_cinecitta(events, from_time, to_time, requests.get(
        'https://www.cinecitta.de/common/ajax.php?bereich=portal&modul_id=101&klasse=vorstellungen&cli_mode=1&com=anzeigen_spielplan'
    ).json())
    events.sort(key=lambda event: event['begin'] + event['name'])
    return events


def format_date(s, now):
    today_date = now.strftime('%Y-%m-%d')
    if today_date in s:
        return s.replace(today_date, 'Heute')
    else:
        return datetime.strptime(s, '%Y-%m-%d %H:%M').strftime('%H:%M, %e. %b')


def write_html(f, events, now, name):
    f.write('''<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
<meta name="theme-color" content="#111"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="black"/>
<meta name="msapplication-navbutton-color" content="#111"/>
<title>Was machen?</title>
<link href="https://fonts.googleapis.com/css?family=Roboto+Mono&display=swap" rel="stylesheet"/>
<style>
head, body {
\tbackground: #222; color: #999;
\tmargin: 0; padding: 0 0 10em;
\tfont-family: 'Roboto Mono', Menlo, monospace;
}

a {
\tcolor: #fff;
\ttext-decoration: none;
}

table {
\tmargin: 0; padding: 0;
\twidth: 100%;
}

td {
\tvertical-align: top;
\tborder-bottom: 1px solid #333;
}

td.Image {
\tmargin: 0; padding: 0;
\tbackground: #111;
}

td.Image img {
\tdisplay: block;
}

td.Details {
\tmargin: 0; padding: .66em 1em;
\twidth: 100%;
}

.When, .Name, .Place {
\tdisplay: block;
}

.Name {
\tpadding: .2em 0;
\tfont-size: 125%;
}

#Search {
\tmargin: 0; padding: 0;
\tposition: fixed;
\tbottom: 0;
\twidth: 100%;
\tz-index: 1;
\tbackground: rgba(0, 0, 0, .75);
}

#DaySelector {
\tdisplay: flex;
\tflex-direction: row;
}

#DaySelector .Day {
\tpadding: 1em 1em 0;
\tflex-grow: 1;
\ttext-align: center;
\tfont-size: min(4vw, 110%);
\tborder-right: 1px solid #333;
}

#DaySelector .Day:last-child {
\tborder: 0;
}

.Active {
\tcolor: #333;
}

#Query {
\tdisplay: none;
\tmargin: 0; padding: 1em;
\tborder: 0;
\toutline: none;
\tbackground: transparent; color: #fff;
\twidth: 100%;
\tfont-family: 'Roboto Mono', Menlo, monospace;
\tfont-size: 110%;
\tline-height: 150%;
}
</style>
</head>
<body>
<div id="Search"><div id="DaySelector">''')
    if name.isdigit():
        name = now.strftime('%a').lower()
    for weekday, label in {
        'mon': 'Mo',
        'tue': 'Di',
        'wed': 'Mi',
        'thu': 'Do',
        'fri': 'Fr',
        'sat': 'Sa',
        'sun': 'So',
    }.items():
        f.write('<a href="%s.html" class="Day%s">%s</a>' % (
            weekday,
            ' Active' if weekday == name else '',
            label,
        ))
    f.write('''</div><input id="Query" type="text" placeholder="Suche"/></div>
<table id="EventsTable">
''')
    for event in events:
        f.write('''<tr><td class="Image"><img
src="%s" alt="%s" width="128"/></td>
<td class="Details"><span class="When">%s</span>
<a class="Name" href="%s">%s</a>
<span class="Place">%s</span></td></tr>
''' % (
            event['image_url'],
            event['name'],
            format_date(event['begin'], now),
            event['url'],
            event['name'],
            event['place'],
        ))
    f.write('''</table>
<script>
'use strict'
const W = window, D = document

function filter(table, value) {
\tvalue = value.toLowerCase()
\tfor (let row of table.rows) {
\t\trow.style.display = row.cells[1].innerText.toLowerCase().indexOf(
\t\t\tvalue
\t\t) > -1 ? 'table-row' : 'none'
\t}
}

W.onload = () => {
\tconst table = D.getElementById('EventsTable'),
\t\tsearch = D.getElementById('Search'),
\t\tquery = D.getElementById('Query')
\tif (table && search && query) {
\t\tlet timer = null
\t\tquery.onkeyup = () => {
\t\t\tif (timer) {
\t\t\t\tclearTimeout(timer)
\t\t\t}
\t\t\ttimer = setTimeout(() => {
\t\t\t\tfilter(table, query.value.trim())
\t\t\t}, 300)
\t\t}
\t\tquery.style.display = 'block'
\t\tquery.focus()
\t}
}
</script>
</body>
</html>
''')


def generate_files(events, now):
    now_date = now.date()
    # generate files that start from every hour of today until the
    # end of the day
    for hour in range(24):
        chunk = []
        for event in events:
            dt = datetime.strptime(event['begin'], '%Y-%m-%d %H:%M')
            date = dt.date()
            if date < now_date or hour > dt.hour:
                continue
            if date > now_date:
                break
            chunk.append(event)
        if len(chunk) > 0:
            yield '%02d' % (hour, ), chunk
    # generate a file for every weekday
    def name_of_day(date):
        return date.strftime('%a').lower()
    chunk = None
    last = None
    for event in events:
        date = datetime.strptime(event['begin'], '%Y-%m-%d %H:%M').date()
        if date != last:
            if chunk is not None:
                yield name_of_day(last), chunk
            chunk = [event]
        else:
            chunk.append(event)
        last = date
    if chunk is not None:
        yield name_of_day(last), chunk


def main(path='.'):
    now = datetime.now()
    events = fetch_events(
        now,
        now + timedelta(days=6)
    )
    for file_name, contents in generate_files(events, now):
        with open('%s/%s.html' % (path, file_name, ), 'w') as f:
            write_html(f, contents, now, file_name)


if __name__ == '__main__':
    main( * sys.argv[1:])
