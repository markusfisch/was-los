'use strict'

function filter(table, value) {
	value = value.toLowerCase()
	for (let row of table.rows) {
		row.style.display = row.cells[1].innerText.toLowerCase().indexOf(
			value
		) > -1 ? 'table-row' : 'none'
	}
}

const D = document,
	table = D.getElementById('EventsTable'),
	search = D.getElementById('Search'),
	query = D.getElementById('Query')

if (table && search && query) {
	let timer = null
	query.onkeyup = () => {
		if (timer) {
			clearTimeout(timer)
		}
		timer = setTimeout(() => {
			filter(table, query.value.trim())
		}, 300)
	}
	query.style.display = 'block'
	query.focus()
}
