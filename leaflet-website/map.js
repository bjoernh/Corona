
  
function style(feature) {
  return {
      fillColor: getColor(feature.properties['InzidenzFallNeu-7-Tage']),
      weight: 1,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.65
  };
};

function getColorInzedenz(d) {
  return d > 100 ? '#800026' :
        d > 75  ? '#BD0026' :
        d > 60  ? '#E31A1C' :
        d > 50  ? '#FC4E2A' :
        d > 30   ? '#FD8D3C' :
        d > 20   ? '#FEB24C' :
        d > 10   ? '#FED976' :
                    '#FFEDA0';
  };

  
function style(feature) {
  return {
      fillColor: getColorInzedenz(feature.properties['InzidenzFallNeu-7-Tage']),
      weight: 1,
      opacity: 1,
      color: 'white',
      dashArray: '3',
      fillOpacity: 0.65
  };
};

function highlightFeature(e) {
    var layer = e.target;

    layer.setStyle({
        weight: 3,
        color: '#666',
        dashArray: '',
        fillOpacity: 0.65
    });

    if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
        layer.bringToFront();
    }
    info.update(layer.feature.properties);
}

var geojson;

function resetHighlight(e) {
    geojson.resetStyle(e.target);
    info.update();
}

function zoomToFeature(e) {
    map.fitBounds(e.target.getBounds());
}

function onEachFeature(feature, layer) {
    layer.on({
        mouseover: highlightFeature,
        mouseout: resetHighlight,
        click: zoomToFeature
    });
}

var map;

var info;


function init() {
     map = L.map('map').setView([51.396, 11.283], 6);
     map.locate({setView: true, maxZoom: 8});
     map.createPane('labels');
     map.getPane('labels').style.zIndex = 650;
     map.getPane('labels').style.pointerEvents = 'none';
     
     let xhr = new XMLHttpRequest();
    xhr.open('GET', 'risk_2021-03-12.geojson');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.responseType = 'json';
    xhr.onload = function() {
        if (xhr.status !== 200) return
        geojson = L.geoJSON(xhr.response, {
            style: style,
            onEachFeature: onEachFeature})
            .addTo(map);
    };
    xhr.send();
    var positron = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png', {
        attribution: '©CartoDB'
        }).addTo(map);

    var positronLabels = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png', {
        attribution: '©CartoDB',
        pane: 'labels'
    }).addTo(map);
     
   var legend = L.control({position: 'bottomright'});

	legend.onAdd = function (map) {

		var div = L.DomUtil.create('div', 'info legend'),
			grades = [0, 10, 20, 30, 50, 75 , 100],
			labels = [],
			from, to;

		for (var i = 0; i < grades.length; i++) {
			from = grades[i];
			to = grades[i + 1];

			labels.push(
				'<i style="background:' + getColorInzedenz(from + 1) + '"></i> ' +
				from + (to ? '&ndash;' + to : '+'));
		}

		div.innerHTML = labels.join('<br>');
		return div;
	};
    legend.addTo(map);
   
    info  = L.control();

    info.onAdd = function (map) {
        this._div = L.DomUtil.create('div', 'info'); // create a div with a class "info"
        this.update();
        return this._div;
    };

    // method that we will use to update the control based on feature properties passed
    info.update = function (props) {
        this._div.innerHTML = (props ? '<h4>' + props.Landkreis + '</h4>' +  
            '7-Tage Inzidenz: ' + Math.round(props['InzidenzFallNeu-7-Tage'])
            + '<br>Kontaktrisiko: 1/' + Math.round(props.Kontaktrisiko) +
            '<br>RwK: ' + props['InzidenzFallNeu-7-Tage-Trend-Spezial'].toFixed(2) +
            '<br>Neue Fälle: ' + props.AnzahlFallNeu +
            '<br>Neue Todefälle: ' + props['AnzahlTodesfallNeu-7-Tage'] +
            '<br>Fallsterblichkeit: ' + props['Fallsterblichkeit-Prozent'].toFixed(2) + '%' +
            '<br>Verworfene Fälle<br> wegen Verzögerung: ' + props['AnzahlFallNeu-7-Tage-Dropped']

            : 'Hover über einen Landkreis');
    };

    info.addTo(map);
    map.attributionControl.setPrefix('Daten vom 12.03.21'); // Don't show the 'Powered by Leaflet' text. Attribution overload


}

