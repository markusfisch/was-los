#!/usr/bin/env python3

import html
import json
import requests
import sys

from datetime import datetime, timedelta
from lxml import etree, html as lxmlhtml


def essence(s):
    # remove all non-alphabetical characters
    e = ''
    for c in s.lower():
        if c.isalpha():
            e += c
        elif not c.isspace():
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
    else:
        if template['source'] not in event['source']:
            event['source'] += ' ' + template['source']
        if not same(event['place'], template['place']):
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

    def first_or(l, preset):
        return l[0] if l else preset

    tree = etree.fromstring(requests.get(uri).content)
    # see https://meineveranstaltungen.nuernberg.de/Export_Schnittstelle.pdf
    for event in tree.xpath('//ERGEBNIS/VERANSTALTUNG'):
        try:
            template = {
                'name': event.xpath('TITEL/text()')[0],
                'place': event.xpath('ORT/text()')[0],
                'image_url': first_or(event.xpath('BILD/text()'), '#'),
                'url': first_or(event.xpath('DETAILLINK/text()'), '#'),
                'source': '#mwz',
            }
            hour = event.xpath('OEFFNUNGSZEITEN')[0]
            t = hour.attrib['TYP']
            if t == '1':
                date = hour.xpath('DATUM')[0]
                add_event(
                    events,
                    from_time,
                    to_time,
                    template,
                    date.text,
                    date.attrib['BEGINN'],
                )
            elif t == '2':
                for date in hour.xpath('DATUM'):
                    add_event(
                        events,
                        from_time,
                        to_time,
                        template,
                        date.text,
                        date.attrib['BEGINN'],
                    )
            elif t == '3':
                days = {}
                # add all weekdays between DATUM1 and DATUM2
                begin = hour.xpath('DATUM1')[0].text
                end = hour.xpath('DATUM2')[0].text
                for open_day in hour.xpath('OFFENETAGE/OFFENERTAG'):
                    for day in collect_days(begin, end, open_day.text):
                        days[day] = open_day.attrib['BEGINN']
                # remove exceptions
                exceptions = hour.xpath('AUSNAHMEN/text()')
                if len(exceptions) > 0:
                    for day in filter(None, exceptions[0].split(';')):
                        days.pop(day, None)
                # overwrite with deviating days
                for dev_day in hour.xpath('ABWEICHENDETAGE/ABWEICHENDERTAG'):
                    days[dev_day.text] = dev_day.attrib['BEGINN']
                for day, time in days.items():
                    add_event(
                        events,
                        from_time,
                        to_time,
                        template,
                        day,
                        time,
                    )
        except IndexError:
            pass


def fetch_curt(events, from_time, to_time, uri):
    current_year = datetime.today().year
    tree = lxmlhtml.fromstring(requests.get(uri).content)
    for eventlist in tree.xpath('//div[@id="eventlist"]'):
        for event in eventlist.xpath(
                'div[@class="content"]/div[@class="event"]'):
            times = event.xpath('div/div/div[@class="time"]')
            dates = event.xpath('div/div/div[@class="dat"]')
            places = event.xpath('div/div/a[@class="loc"]')
            titles = event.xpath('div/div/div[@class="titel"]/a')
            if (len(times) < 1 or
                len(dates) < 1 or
                len(places) < 1 or
                len(titles) < 1):
                continue
            template = {
                'name': titles[0].text,
                'image_url':
                    'https://www.curt.de/nbg/templates/css/icon_logo.svg',
                'url': titles[0].attrib['href'],
                'place': places[0].text,
                'source': '#curt',
            }
            date = datetime.strptime(
                dates[0].text,
                '%d.%m.'
            ).replace(year=current_year).strftime('%Y-%m-%d')
            time = times[0].text.replace('.', ':')
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
            'source': '#cinecitta',
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
    def unpack_url(url):
        if url.startswith('//'):
            url = url[2:]
        if url.startswith('http://'):
            return url
        if url.startswith('https://'):
            return url
        return 'https://' + url

    lazy_attrib = 'data-pagespeed-lazy-src'
    tree = lxmlhtml.fromstring(requests.get(uri).content)
    for theater in tree.xpath('//li[@class="cinemaprogram-cinema"]'):
        names = theater.xpath('div[@class="cinemaprogram-meta"]/h3/a')
        if len(names) < 1:
            continue
        theater_name = names[0].text
        for movie in theater.xpath(
            'div[@class="cinema-movies-container"]/ul/li'
        ):
            posters = movie.xpath('article/div[@class="card-media"]/img')
            if len(posters) < 1:
                continue
            movie_poster = (posters[0].attrib[lazy_attrib] if
                lazy_attrib in posters[0].attrib else posters[0].attrib['src'])
            titles = movie.xpath('article/div[@class="card-body"]/h3/a')
            if len(titles) < 1:
                continue
            movie_url = titles[0].attrib['href']
            movie_name = titles[0].text
            template = {
                'name': movie_name,
                'place': theater_name,
                'image_url': unpack_url(movie_poster),
                'url': unpack_url(movie_url),
                'source': '#kino',
            }
            showings = movie.xpath('ol/li/a/time')
            if len(showings) < 1:
                continue
            for showing in showings:
                datetime = showing.attrib['datetime'].split(' ')
                if len(datetime) < 2:
                    continue
                add_event(
                    events,
                    from_time,
                    to_time,
                    template,
                    datetime[0],
                    datetime[1],
                )


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
<html lang="de">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
<meta name="theme-color" content="#111"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="black"/>
<meta name="msapplication-navbutton-color" content="#111"/>
<title>Was machen in Nürnberg, Fürth und Erlangen?</title>
<link rel="apple-touch-icon" href="icon_ios.png"/>
<link rel="manifest" href="manifest.json"/>
<link href="https://fonts.googleapis.com/css?family=Roboto+Mono&display=swap" rel="stylesheet"/>
<style>''')
    f.write(style)
    f.write('''</style>
<script defer src="main.js"></script>
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
    f.write('''</div><input id="Query" type="text"
placeholder="Suche nach X ohne !Y"/></div>
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
<span class="Source">%s</span><br/>
<a class="Name" %shref="%s">%s</a><br/>
<address class="Place">%s</address></td></tr>
''' % (
            event['image_url'],
            html.escape(event['name']),
            event['begin'],
            dt.strftime('Heute %H:%M' if name_is_digit else '%H:%M, %e. %b'),
            html.escape(event['source']),
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
