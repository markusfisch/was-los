'use strict'

function clearQuery() {
	filter(table, query.value = '')
}

function filter(table, term) {
	function indexOf(haystack, needles) {
		let visible = true
		for (let i = 0, l = needles.length; i < l; ++i) {
			const needle = needles[i]
			if (needle[0] == '!') {
				if (visible && needle.length > 1) {
					visible = haystack.indexOf(needle.substr(1)) < 0
				}
			} else if (visible && haystack.indexOf(needle) < 0) {
				visible = false
			}
		}
		return visible
	}
	const values = term.trim().toLowerCase().split(' ').filter(v => v != '')
	for (const row of table.rows) {
		row.style.display = indexOf(
			row.cells[1].innerText.toLowerCase(),
			values
		) ? 'table-row' : 'none'
	}
	dayTimes.style.display = values.length > 0 ? 'none' : 'flex'
	for (let a of dayLinks) {
		a.href = a.originalHref + '?' + encodeURI(term)
	}
}

const D = document,
	W = window,
	table = D.getElementById('EventsTable'),
	search = D.getElementById('Search'),
	queryBar = D.getElementById('QueryBar'),
	query = D.getElementById('Query'),
	dayPicker = D.getElementById('DayPicker'),
	dayTimes = D.getElementById('DayTimes')

let dayLinks

if (table && search && query) {
	let timer = null
	query.onkeyup = () => {
		if (timer) {
			clearTimeout(timer)
		}
		timer = setTimeout(() => {
			filter(table, query.value)
			W.scrollTo(0, 0)
		}, 300)
	}
	queryBar.style.display = 'flex'
	query.focus()
	dayLinks = dayPicker.getElementsByTagName('a')
	for (let a of dayLinks) {
		a.originalHref = a.href
	}
	const search = W.location.search
	if (search) {
		query.value = search.substr(1)
		filter(table, query.value)
	}
}

W.onload = () => {
	const term = query.value
	if (term) {
		filter(table, term)
	}
}

if ('serviceWorker' in navigator) {
	navigator.serviceWorker.register('service-worker.js')
}
