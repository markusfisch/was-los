#!/usr/bin/env python3

import html
import json
import pytz
import re
import requests
import sys
import traceback

from datetime import datetime, timedelta
from lxml import html as lxml_html
from urllib.parse import urljoin


def parse_date(s):
    if s is None or s == '':
        return None
    try:
        if s.endswith('Z'):
            utc = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return utc.astimezone(pytz.timezone("Europe/Berlin"))
        else:
            return datetime.fromisoformat(s)
    except:
        print("cannot parse date: %s" % (s, ))
        return None


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
    for p in map(lambda s: s.lstrip(), places.split(',')):
        if place_essence == essence(p):
            return True
    return False


def ensure_https(url):
    return url.replace('http://', 'https://')


def add_event(events, from_time, to_time, template, day, begin):
    begin = day + ' ' + (begin if begin != "" else '00:00')
    begin_date = parse_date(begin)
    if begin_date is None or begin_date < from_time or begin_date > to_time:
        return
    template['name'] = html.unescape(template['name'])
    template['place'] = html.unescape(template['place'])
    template['begin'] = begin
    template['image_url'] = ensure_https(template['image_url'])
    template['url'] = ensure_https(template['url'])
    key = begin + essence(template['name'])
    event = events.get(key)
    if event is None:
        events[key] = template.copy()
    else:
        if template['source'] not in event['source']:
            event['source'] += ' ' + template['source']
        if not same(event['place'], template['place']):
            event['place'] += ', ' + template['place']


def fetch_vk_nuernberg(events, from_time, to_time, uri):
    url_template = 'https://www.nuernberg.de/internet/stadtportal/nbg_veranstaltungen.html?r=8&miniweb=stadtportal&vid=%s_%sT%s#vk_detail#'
    max_date = datetime.today() + timedelta(days=7)

    def add_vk_nuernberg_event(date, time):
        template['url'] = url_template % (vid, date, time, )
        add_event(events, from_time, to_time, template, date, time)

    evs = requests.get(uri).json()
    for item in evs['VERANSTALTUNGEN']:
        place = item['ORT']
        if place is None:
            continue
        template = {
            'name': item['TITEL'],
            'place': place,
            'image_url': item['BILD'][0]['sn'],
            'source': '#vknuernberg',
        }
        vid = item['VERANSTALTUNGID']
        dates = item['DATUM']
        info = dates[1]
        t = info['SCHEMATYP'] if 'SCHEMATYP' in info else 0
        if t == 0:
            for day_time in dates[0]:
                parts = re.split(r'[A-Z]', day_time)
                add_vk_nuernberg_event(parts[0], parts[1])
        elif t == 1:
            step = info['TAEGLICHXTEN']
            tt = info['TAEGLICHTYP']
            end = info['ZEITRAUMENDE']
            if len(end) == 8:
                end = '20' + end
            end = parse_date(end)
            if end is None:
                continue
            end = min(max_date, end)
            for day_time in dates[0]:
                parts = re.split(r'[A-Z]', day_time)
                day = parse_date(parts[0])
                if day is None:
                    continue
                while day < end:
                    if tt == 1 or day.weekday() < 5:
                        add_vk_nuernberg_event(
                            day.strftime('%Y-%m-%d'),
                            parts[1],
                        )
                    day += timedelta(days=step)
        elif t == 2:
            weekday_to_key = {
                0: 'WOMO',
                1: 'WODI',
                2: 'WOMI',
                3: 'WODO',
                4: 'WOFR',
                5: 'WOSA',
                6: 'WOSO',
            }
            step = info['WOCHEXTE'] * 7
            end = parse_date(info['ZEITRAUMENDE'])
            if end is None:
                continue
            end = min(max_date, end)
            for day_time in dates[0]:
                parts = re.split(r'[A-Z]', day_time)
                day = parse_date(parts[0])
                if day is None:
                    continue
                while day < end:
                    offset = day
                    for i in range(7):
                        if info[weekday_to_key[offset.weekday()]] > 0:
                            add_vk_nuernberg_event(
                                offset.strftime('%Y-%m-%d'),
                                parts[1],
                            )
                        offset += timedelta(days=1)
                    day += timedelta(days=step)


def fetch_cinecitta(events, from_time, to_time, uri):
    base_url = 'https://www.cinecitta.de'
    session = requests.Session()
    response = session.get(uri, timeout=30)
    response.raise_for_status()
    document = lxml_html.fromstring(response.text)

    def build_weekday_lookup():
        lookup = {}
        for node in document.xpath("//input[@name='tx_filmapi_list[weekdays][]']"):
            iso_value = node.get('value')
            dt = parse_date(iso_value)
            if dt is None:
                continue
            lookup[dt.strftime('%d.%m')] = dt
        return lookup

    weekday_lookup = build_weekday_lookup()

    def infer_date(day_key, fallback):
        day, month = map(int, day_key.split('.'))
        year = fallback.year
        candidate = datetime(year, month, day)
        if candidate < fallback - timedelta(days=180):
            candidate = datetime(year + 1, month, day)
        elif candidate - fallback > timedelta(days=200):
            candidate = datetime(year - 1, month, day)
        return candidate

    def resolve_header_dates(table):
        dates = []
        previous = None
        headers = table.xpath(".//thead//th[position()>1]")
        for header in headers:
            text = ''.join(header.itertext())
            match = re.search(r'(\d{2}\.\d{2})', text)
            if not match:
                dates.append(None)
                continue
            key = match.group(1)
            dt = weekday_lookup.get(key)
            if dt is None:
                dt = previous + timedelta(days=1) if previous else infer_date(
                    key,
                    from_time,
                )
            if previous is not None:
                while dt < previous:
                    dt = datetime(dt.year + 1, dt.month, dt.day)
            dates.append(dt)
            previous = dt
        return dates

    def parse_fragment(html_fragment):
        wrapper = lxml_html.fromstring('<ul>%s</ul>' % html_fragment)
        return wrapper.xpath(".//li[contains(@class,'filmapi-container__list--li')]")

    def fetch_additional_film_nodes():
        form = document.xpath("//form[@id='loadMoreFilms']")
        if not form:
            return []
        form = form[0]
        action = urljoin(base_url, form.get('action'))
        data = {}
        for field in form.xpath(".//input[@name]"):
            name = field.get('name')
            data[name] = field.get('value') or ''
        limit = int(data.get('tx_filmapi_list[limit]', '0') or 0)
        total = int(data.get('tx_filmapi_list[allFilmss]', '0') or 0)
        offset = int(data.get('tx_filmapi_list[offset]', '0') or 0)
        if limit <= 0 or total <= offset:
            return []
        nodes = []
        headers = {'X-Requested-With': 'XMLHttpRequest'}
        while offset < total:
            payload = data.copy()
            payload['tx_filmapi_list[offset]'] = str(offset)
            try:
                more = session.post(action, data=payload, headers=headers, timeout=30)
                more.raise_for_status()
                content = more.json().get('content', '')
            except Exception as exc:
                print('cinecitta loadMore failed: %s' % (exc, ))
                break
            if not content.strip():
                break
            nodes.extend(parse_fragment(content))
            offset += limit
        return nodes

    def absolute_url(path):
        if not path:
            return ''
        return ensure_https(urljoin(base_url, path))

    film_nodes = document.xpath("//li[contains(@class,'filmapi-container__list--li')]")
    film_nodes.extend(fetch_additional_film_nodes())

    for film in film_nodes:
        name = ''.join(
            film.xpath(".//div[contains(@class,'filmapi-container__list--header')]//h3/text()")
        ).strip()
        if not name:
            continue
        url_node = film.xpath(".//a[contains(@href, '/filme/')][1]/@href")
        image_node = film.xpath(".//div[contains(@class,'w-poster')]//img/@src")
        base_template = {
            'name': name,
            'image_url': absolute_url(image_node[0]) if image_node else '',
            'url': absolute_url(url_node[0]) if url_node else uri,
            'source': '#cinecitta',
        }
        showtime_sections = film.xpath(".//div[contains(@class,'show_playing_times__content')]")
        if not showtime_sections:
            continue
        for center_header in showtime_sections[0].xpath(".//div[@data-index]"):
            center_name = ''.join(
                center_header.xpath(".//span[contains(@class,'font-semibold')]/text()")
            ).strip()
            if not center_name:
                center_name = ''.join(center_header.xpath(".//span/text()")).strip()
            sibling = center_header.getnext()
            while sibling is not None and not isinstance(getattr(sibling, 'tag', None), str):
                sibling = sibling.getnext()
            if sibling is None:
                continue
            tables = sibling.xpath(".//table")
            if not tables:
                continue
            table = tables[0]
            header_dates = resolve_header_dates(table)
            rows = table.xpath(".//tbody/tr")
            for row in rows:
                screen_name = ''.join(
                    row.xpath(".//th//div[contains(@class,'font-semibold')]/text()")
                ).strip()
                if not screen_name:
                    continue
                place = '%s %s' % (center_name, screen_name)
                cells = row.xpath('.//td')
                for cell, day_dt in zip(cells, header_dates):
                    if day_dt is None:
                        continue
                    day = day_dt.strftime('%Y-%m-%d')
                    for link in cell.xpath(".//a[contains(@class,'performance-link')]"):
                        time_text = ''.join(
                            link.xpath(".//span[contains(@class,'link-text')]/text()")
                        ).strip()
                        if not time_text:
                            continue
                        template = base_template.copy()
                        template['place'] = place
                        add_event(
                            events,
                            from_time,
                            to_time,
                            template,
                            day,
                            time_text,
                        )


def fetch_kino(events, from_time, to_time, city_id):
    api_base = 'https://kntkapi.apps.stroeermb.de/api/'

    root = requests.get(api_base + 'city/' + city_id + '/').json()
    cinema_ids = set()
    for cinemas in root['cinemas_by_movie']:
        for cinema in cinemas['cinemas']:
            cinema_ids.add(cinema['id'])
    unique_cinema_ids = sorted(list(cinema_ids))

    for cinema_id in unique_cinema_ids:
        cinema = requests.get(api_base + 'cinema/' + cinema_id + '/').json()
        cinema_name = cinema['name']
        movies = {}
        for movie in cinema['movies']:
            movies[movie['id']] = {
                'name': movie['title'],
                'image_url': movie['media']['poster_url'],
            }
        for showtime in cinema['showtimes']:
            movie_id = showtime['movie']['id']
            movie = movies.get(movie_id)
            if movie is None:
                continue
            template = {
                'name': movie['name'],
                'image_url': movie['image_url'],
                'place': cinema_name,
                'url': showtime['ticket_purchase_url'],
                'source': '#kino',
            }
            dt = parse_date(showtime['showtime'])
            if dt is None:
                continue
            add_event(
                events,
                from_time,
                to_time,
                template,
                dt.strftime('%Y-%m-%d'),
                dt.strftime('%H:%M'),
            )


def fetch_events(from_time, to_time):
    # use a dict to be able to merge events
    events = {}
    for source in [
        (fetch_vk_nuernberg, 'https://vk.nuernberg.de/export.php'),
        (fetch_cinecitta, 'https://www.cinecitta.de/programm/'),
        (fetch_kino, '7903'),
        (fetch_kino, '3195'),
        (fetch_kino, '2731'),
    ]:
        count = len(events)
        # try all sources separately to allow failures
        try:
            source[0](events, from_time, to_time, source[1])
        except Exception as e:
            print(traceback.format_exc())
        if len(events) == count:
            print('%s did not add any events.' % (source[1], ))
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
<title>Was ist los in Nürnberg, Fürth und Erlangen?</title>
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
    f.write('</div><div id="DayPicker" class="Picker">''')
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
    f.write('''</div><div id="QueryBar"><input id="Query" type="text"
placeholder="Suche nach X ohne !Y"/><a id="Clear"
onclick="clearQuery()">x</a></div></div>
<table id="EventsTable">''')
    time_marks_keys = list(time_marks.keys())
    mark_index = 0
    mark = time_marks_keys[mark_index]
    for event in events:
        dt = parse_date(event['begin'])
        if dt is None:
            continue
        if dt.hour >= mark:
            anchor_tag = 'name="%d" ' % (dt.hour, )
            mark_index += 1
            mark = time_marks_keys[mark_index] if mark_index < len(
                time_marks_keys) else 99
        else:
            anchor_tag = ''
        source = event['source']
        place = event['place']
        name = event['name']
        f.write('''<tr><td class="Image"><img
src="%s" alt="%s" width="128" loading="lazy"/></td>
<td class="Details"><time datetime="%s" class="When">%s</time>
<span class="Source">%s</span><br/>
<a class="Name" %shref="%s">%s</a><br/>
<address class="Place">%s</address></td></tr>
''' % (
            event['image_url'],
            html.escape(event['name']),
            event['begin'],
            dt.strftime('Heute %H:%M' if name_is_digit else '%H:%M, %e. %b'),
            html.escape(source),
            anchor_tag,
            event['url'],
            html.escape(name),
            html.escape(place),
        ))
    f.write('''</table>
<div id="Disclaimer">
Alle Inhalte sind Eigentum der jeweilig verlinkten Quelle.
Den Quellcode zu dieser Seite finden Sie
<a href="https://github.com/markusfisch/was-los">hier</a>.
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
            dt = parse_date(event['begin'])
            if dt is None or dt < from_time:
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
    events = fetch_events(today_start, today_start + timedelta(days=7))
    for file_name, contents in generate_files(events, today):
        with open('%s/%s.html' % (path, file_name, ), 'w') as f:
            write_html(f, style, contents, today, file_name)


if __name__ == '__main__':
    main( * sys.argv[1:])
