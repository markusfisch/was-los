#!/usr/bin/env python3

import html
import json
import requests
import sys
import untangle

from datetime import datetime, timedelta


def essence(s):
    # remove all non-alphabetical characters
    e = ''
    for c in s.lower():
        if c.isalpha():
            e += c
        elif c != ' ':
            # break at first character that is not a space to loose
            # optional subtitles
            break
    return e


def same(places, place):
    # check if the given place is in the comma separated list of places
    place_essence = essence(place)
    for p in map(lambda s : s.lstrip(), places.split(',')):
        if place_essence == essence(p):
            return True
    return False


def add_event(events, from_time, to_time, template, day, begin):
    begin = day + ' ' + (begin if begin != "" else '00:00')
    begin_date = datetime.strptime(begin, '%Y-%m-%d %H:%M')
    if begin_date < from_time or begin_date > to_time:
        return
    template['name'] = html.unescape(template['name'])
    template['place'] = html.unescape(template['place'])
    template['begin'] = begin
    key = begin + essence(template['name'])
    event = events.get(key)
    if event is None:
        events[key] = template.copy()
    elif not same(event['place'], template['place']):
        event['place'] += ', ' + template['place']


def fetch_meine_veranstaltungen(events, from_time, to_time, uri):
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

    # see https://meineveranstaltungen.nuernberg.de/Export_Schnittstelle.pdf
    for event in untangle.parse(uri).ERGEBNIS.VERANSTALTUNG:
        elements_in_event = dir(event)
        template = {
            'name': event.TITEL.cdata,
            'place': event.ORT.cdata,
            'image_url': event.BILD.cdata if
                'BILD' in elements_in_event else '#',
            'url': event.DETAILLINK.cdata if
                'DETAILLINK' in elements_in_event else '#',
            'source': 'mwz',
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
                )
        elif t == '3' or 'OFFENETAGE' in elements_in_hours:
            days = {}
            # add all weekdays between DATUM1 and DATUM2
            begin = hours.DATUM1.cdata
            end = hours.DATUM2.cdata
            if 'OFFENETAGE' in elements_in_hours:
                for d in hours.OFFENETAGE.OFFENERTAG:
                    for day in collect_days(begin, end, d.cdata):
                        days[day] = d['BEGINN']
            # remove exceptions
            if 'AUSNAHMEN' in elements_in_hours:
                for day in filter(None, hours.AUSNAHMEN.cdata.split(';')):
                    days.pop(day, None)
            # overwrite with deviating days
            if ('ABWEICHENDETAGE' in elements_in_hours and
                'ABWEICHENDERTAG' in dir(hours.ABWEICHENDETAGE)):
                for d in hours.ABWEICHENDETAGE.ABWEICHENDERTAG:
                    days[d.cdata] = d['BEGINN']
            for day, time in days.items():
                add_event(
                    events,
                    from_time,
                    to_time,
                    template,
                    day,
                    time,
                )


def fetch_curt(events, from_time, to_time, uri):
    current_year = datetime.today().year
    html = requests.get(uri).text
    start = html.find('<div id="eventlist"')
    while start > -1:
        start = html.find('<div class="event"', start)
        if start < 0:
            break
        # find time
        start = html.index('<div class="time">', start)
        stop = html.index('</', start)
        time = html[html.index('>', start) + 1:stop].replace('.', ':')
        # find date
        start = html.index('<div class="dat">', start)
        stop = html.index('</', start)
        date = datetime.strptime(
            html[html.index('>', start) + 1:stop],
            '%d.%m.'
        ).replace(year=current_year).strftime('%Y-%m-%d')
        # find place
        start = html.index('<a class="loc"', start)
        stop = html.index('</', start)
        place = html[html.index('>', start) + 1:stop]
        # find url
        start = html.index('<div class="titel">', start)
        start = html.index(' href=', start)
        start = html.index('"', start) + 1
        url = html[start:html.index('"', start)]
        # find name
        stop = html.index('</', start)
        name = html[html.index('>', start) + 1:stop]
        # add event
        template = {
            'name': name,
            'image_url': 'https://www.curt.de/nbg/templates/css/icon_logo.svg',
            'url': url,
            'place': place,
            'source': 'curt',
        }
        add_event(
            events,
            from_time,
            to_time,
            template,
            date,
            time,
        )


def fetch_cinecitta(events, from_time, to_time, uri):
    shows = requests.get(uri).json()
    for item in shows['daten']['items']:
        template = {
            'name': item['film_titel'],
            'image_url': item['film_cover_src'],
            'url': 'https://www.cinecitta.de/' + item['filminfo_href'],
            'source': 'cinecitta',
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
                    )


def fetch_kino(events, from_time, to_time, uri):
    def extract_cdate_attrib(tag, attrib, text, start):
        try:
            start = text.index('<%s ' % (tag, ), start)
            start = text.index('%s="' % (attrib, ), start)
            start = text.index('"', start) + 1
            attrib = text[start:text.index('"', start)]
            start = text.index('>', start)
            stop = text.index('<', start)
            return stop, text[start + 1:stop], attrib
        except ValueError:
            return start, "", ""

    def extract_attrib(tag, attrib, text, start):
        try:
            start = text.index('<%s ' % (tag, ), start)
            start = text.index('%s="' % (attrib, ), start)
            start = text.index('"', start) + 1
            stop = text.index('"', start)
            return stop, text[start:stop]
        except ValueError:
            return start, "", ""

    def unpack_url(url):
        if url.startswith('//'):
            url = url[2:]
        if url.startswith('http://'):
            return url
        if url.startswith('https://'):
            return url
        return 'https://' + url

    html = requests.get(uri).text
    # find first theater
    theater_header = 'class="cinemaprogram-cinema"'
    i = html.find(theater_header)
    while i > -1:
        # find name of theater
        i, theater, href = extract_cdate_attrib('a', 'href', html, i)
        # find optional next theater to know where to stop iterating
        # screenings
        next_theater = html.find(theater_header, i)
        # find optional screenings for that theater
        while i > -1:
            i = html.find('<li class="cinema-movie bob', i)
            if i < 0 or (next_theater > -1 and i > next_theater):
                # those screenings belong to the next theater
                i = next_theater
                break
            i, image_url = extract_attrib('img', 'src', html, i)
            i, movie, href = extract_cdate_attrib('a', 'href', html, i)
            # find optional times
            i = html.find('schedules-container', i)
            if i < 0:
                continue
            template = {
                'name': movie,
                'place': theater,
                'image_url': unpack_url(image_url),
                'url': unpack_url(href),
                'source': 'kino',
            }
            # iterate over optional times inside <ol></ol>
            end_of_list = html.find('</ol>', i)
            while end_of_list > -1:
                i = html.find('<time', i)
                if i < 0 or i > end_of_list:
                    i = end_of_list
                    break
                i, time, date = extract_cdate_attrib('time', 'datetime',
                    html, i)
                add_event(
                    events,
                    from_time,
                    to_time,
                    template,
                    date.split(' ')[0],
                    time,
                )
        i = next_theater


def fetch_events(from_time, to_time):
    # use a dict to be able to merge events
    events = {}
    for source in [
        (fetch_meine_veranstaltungen,
                'http://meine-veranstaltungen.net/export.php5'),
        (fetch_curt, 'https://www.curt.de/nbg/termine/'),
        (fetch_cinecitta, 'https://www.cinecitta.de/common/ajax.php?' +
                'bereich=portal&modul_id=101&klasse=vorstellungen&' +
                'cli_mode=1&com=anzeigen_spielplan'),
        (fetch_kino, 'https://www.kino.de/kinoprogramm/stadt/nuernberg/'),
        (fetch_kino, 'https://www.kino.de/kinoprogramm/stadt/fuerth/'),
        (fetch_kino, 'https://www.kino.de/kinoprogramm/stadt/erlangen/'),
    ]:
        # try all sources separately to allow failures
        try:
            source[0](events, from_time, to_time, source[1])
        except Exception as e:
            print(str(e))
    # now we need a list to sort the events by time and name
    events = [v for v in events.values()]
    events.sort(key=lambda event: event['begin'] + event['name'])
    return events


def write_html(f, style, events, today, name):
    f.write('''<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
<meta name="theme-color" content="#111"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="black"/>
<meta name="msapplication-navbutton-color" content="#111"/>
<title>Was machen in Nürnberg, Fürth und Erlangen?</title>
<link rel="apple-touch-icon-precomposed" href="icon_ios.png"/>
<link rel="manifest" href="manifest.json"/>
<link href="https://fonts.googleapis.com/css?family=Roboto+Mono&display=swap" rel="stylesheet"/>
<style>''')
    f.write(style)
    f.write('''</style>
<script defer src="search.js"></script>
</head>
<body>
<div id="Search"><div id="DayTimes" class="Picker">''')
    name_is_digit = name.isdigit()
    time_marks = {
        9: 'Morgens',
        12: 'Mittags',
        19: 'Abends',
        22: 'Nachts',
    }
    current_weekday = today.strftime('%a').lower()
    for hour, label in time_marks.items():
        if name is current_weekday or (name_is_digit and hour >= int(name)):
            href = '#%d' % (hour, )
        elif name_is_digit:
            href = '%02d.html' % (hour, )
        else:
            href = '%s.html#%d' % (name, hour, )
        f.write('<a href="%s" class="Pick">%s</a>' % (href, label, ))
    f.write('</div><div class="Picker">''')
    if name_is_digit:
        name = current_weekday
    for filename, label in {
        'mon': 'Mo',
        'tue': 'Di',
        'wed': 'Mi',
        'thu': 'Do',
        'fri': 'Fr',
        'sat': 'Sa',
        'sun': 'So',
    }.items():
        f.write('<a href="%s.html" class="Pick%s">%s</a>' % (
            filename,
            ' Active' if filename == name else '',
            label,
        ))
    f.write('''</div><input id="Query" type="text" placeholder="Suche"/></div>
<table id="EventsTable">''')
    time_marks_keys = list(time_marks.keys())
    mark_index = 0
    mark = time_marks_keys[mark_index]
    for event in events:
        dt = datetime.strptime(event['begin'], '%Y-%m-%d %H:%M')
        if dt.hour >= mark:
            anchor_tag = 'name="%d" ' % (dt.hour, )
            mark_index += 1
            mark = time_marks_keys[mark_index] if mark_index < len(
                time_marks_keys) else 99
        else:
            anchor_tag = ''
        f.write('''<tr><td class="Image"><img
src="%s" alt="%s" width="128"/></td>
<td class="Details"><time datetime="%s" class="When">%s</time>
<span class="Source">#%s</span><br/>
<a class="Name" %shref="%s">%s</a><br/>
<address class="Place">%s</address></td></tr>
''' % (
            event['image_url'],
            html.escape(event['name']),
            event['begin'],
            dt.strftime('Heute %H:%M' if name_is_digit else '%H:%M, %e. %b'),
            event['source'],
            anchor_tag,
            event['url'],
            html.escape(event['name']),
            html.escape(event['place']),
        ))
    f.write('''</table>
<div id="Disclaimer">
Alle Inhalte sind Eigentum der jeweilig verlinkten Quelle.
Den Quellcode zu dieser Seite finden Sie
<a href="https://github.com/markusfisch/was-machen">hier</a>.
</div>
</body>
</html>
''')


def generate_files(events, today):
    def filter_events(events, from_time):
        # let days end at 3'o clock
        to_time = from_time + timedelta(days=1)
        to_time = datetime(
            to_time.year,
            to_time.month,
            to_time.day,
            3
        )
        chunk = []
        for event in events:
            dt = datetime.strptime(event['begin'], '%Y-%m-%d %H:%M')
            if dt < from_time:
                continue
            if dt > to_time:
                break
            chunk.append(event)
        return chunk

    # generate files that start from every hour of today until the
    # end of the day
    for hour in range(24):
        # yield even if chunk is empty so there will be a file for it
        yield '%02d' % (hour, ), filter_events(
            events,
            datetime(today.year, today.month, today.day, hour),
        )
    # generate a file for every weekday
    dt = datetime(today.year, today.month, today.day)
    for i in range(7):
        # yield even if chunk is empty so there will be a file for it
        yield dt.strftime('%a').lower(), filter_events(events, dt)
        dt += timedelta(days=1)


def main(path='.', stylesheet='screen.css'):
    # Embed style sheet to avoid unstyled display when the resource isn't
    # loaded in time, e.g. on a mobile connection. It's small enough to not
    # add any noticeable weight so that's the better option.
    style = open(stylesheet, 'r').read()
    today = datetime.today()
    # today at 00:00
    today_start = datetime(today.year, today.month, today.day)
    events = fetch_events(today_start, today_start + timedelta(days=6))
    for file_name, contents in generate_files(events, today):
        with open('%s/%s.html' % (path, file_name, ), 'w') as f:
            write_html(f, style, contents, today, file_name)


if __name__ == '__main__':
    main( * sys.argv[1:])
