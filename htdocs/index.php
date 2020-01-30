<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width"/>
<title>Was machen?</title>
<link href="https://fonts.googleapis.com/css?family=Roboto+Mono&display=swap" rel="stylesheet"/>
<style>
head, body {
	background: #222; color: #999;
	margin: 0; padding: 0;
	font-family: 'Roboto Mono', Menlo, monospace;
	font-size: 110%;
	line-height: 150%;
}

a {
	color: #fff;
	text-decoration: none;
}

table {
	margin: 0; padding: 0;
	width: 100%;
}

td {
	vertical-align: top;
	border-bottom: 1px solid #333;
}

td.Image {
	margin: 0; padding: 0;
}

td.Image img {
	display: block;
}

td.Details {
	margin: 0; padding: .66em 1em;
	width: 100%;
}

.When {
	display: block;
}

.Name {
	display: block;
	font-size: 120%;
}

.Place {
	display: block;
	font-size: 80%;
}

#Search {
	margin: 0; padding: 0;
	position: fixed;
	bottom: 0;
	width: 100%;
	z-index: 1;
}

#Query {
	margin: 0; padding: 1em;
	border: 0;
	outline: none;
	background: rgba(0, 0, 0, .75); color: #fff;
	width: 100%;
	font-family: 'Roboto Mono', Menlo, monospace;
	font-size: 110%;
	line-height: 150%;
}
</style>
</head>
<body>
<div id="Search"><input id="Query" type="text" placeholder="Suche"/></div>
<table id="EventsTable">
<?php
$today = date('%Y-%m-%d')
$from_date = date();
$to_date = strtotime("+1 days");
$events = json_decode('events.json');
foreach ($events as &$event) {
	$date = strptime($event['begin'], '%Y-%m-%d %H:%M');
	if ($date < $from_date) {
		continue;
	}
	if ($date > $to_date) {
		return;
	}
	$when = $date == $today ? 'Heute' : strftime('%e. %b %H:%M', $date);
?>
<tr><td class="Image"><img src="<?= $event['image_url'] ?>" alt="<?=
	$event['name'] ?>" width="128"/></td>
<td class="Details"><span class="When"><?= $when ?></span>
<a class="Name" href="<?= $event['url'] ?>"><?= $event['name'] ?></a>
<span class="Place"><?= $event['place'] ?></span></td></tr>
<?php
}
?>
</table>
<script>
'use strict'

function filter(table, value) {
	value = value.trim().toLowerCase()
	for (let row of table.rows) {
		row.style.display = row.cells[1].innerText.toLowerCase().indexOf(
			value
		) > -1 ? 'table-row' : 'none'
	}
}

window.onload = () => {
	const D = document,
		table = D.getElementById('EventsTable'),
		query = D.getElementById('Query')
	let timer = null
	query.onkeyup = () => {
		if (timer) {
			clearTimeout(timer)
		}
		timer = setTimeout(() => {
			filter(table, query.value)
		}, 300)
	}
	query.focus()
}
</script>
</body>
</html>
