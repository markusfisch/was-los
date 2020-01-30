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


if __name__ == '__main__':
    now = datetime.now()
    events = fetch_events(
        now,
        now + timedelta(days=6)
    )
    with open('htdocs/events.json', 'w') as f:
        json.dump(events, f)
