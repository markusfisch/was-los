'use strict'

function exclude(what) {
	what = what.split(' ')[0] + ' '
	let s = query.value + ' '
	const excl = '!' + what
	if (s.indexOf(excl) < 0) {
		s += excl
		query.value = s.trim()
		filter(table, query.value)
	}
}

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
}

const D = document,
	W = window,
	table = D.getElementById('EventsTable'),
	search = D.getElementById('Search'),
	queryBar = D.getElementById('QueryBar'),
	query = D.getElementById('Query'),
	dayTimes = D.getElementById('DayTimes')

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
	for (const e of D.getElementsByClassName('Exclude')) {
		e.style.display = 'block'
	}
}

if ('serviceWorker' in navigator) {
	navigator.serviceWorker.register('service-worker.js')
}
