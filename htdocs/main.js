'use strict'

function filter(table, query) {
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

if ('serviceWorker' in navigator) {
	navigator.serviceWorker.register('service-worker.js')
	const installNote = D.getElementById('AddToHomeScreen')
	let deferredPrompt
	window.addEventListener('beforeinstallprompt', (e) => {
		deferredPrompt = e
		installNote.style.display = 'block'
	})
	installNote.onclick = () => {
		installNote.style.display = 'none'
		if (deferredPrompt) {
			deferredPrompt.prompt()
			deferredPrompt = null
		}
	}
}
