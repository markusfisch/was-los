'use strict'

function filter(table, query) {
	function indexOf(haystack, needles) {
		for (let i = 0, l = needles.length; i < l; ++i) {
			const needle = needles[i]
			if (haystack.indexOf(needle) < 0) {
				return false
			}
		}
		return true
	}
	const values = query.trim().toLowerCase().split(' ').filter(v => v != '')
	for (const row of table.rows) {
		row.style.display = indexOf(
			row.cells[1].innerText.toLowerCase(),
			values
		) ? 'table-row' : 'none'
	}
	dayTimes.style.display = values.length > 0 ? 'none' : 'flex'
}

const D = document,
	table = D.getElementById('EventsTable'),
	search = D.getElementById('Search'),
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
		}, 300)
	}
	query.style.display = 'block'
	query.focus()
}
