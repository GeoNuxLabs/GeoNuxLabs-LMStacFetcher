HTML = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>

  <style>
    html, body { margin:0; height:100%; }
    #map { height:100%; }
  </style>
</head>
<body>

<div id="map"></div>

<script>
  var map = L.map('map').setView([63, 15], 5);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(map);

  var firstCorner = null;
  var previewRect = null;
  var finalRect = null;

  // Setup QWebChannel
  new QWebChannel(qt.webChannelTransport, function(channel) {
    window.pyObj = channel.objects.pyObj;
  });

  // Mouse move → preview rectangle
  map.on('mousemove', function(e) {
    if (!firstCorner) return;

    var secondCorner = [e.latlng.lat, e.latlng.lng];

    var south = Math.min(firstCorner[0], secondCorner[0]);
    var north = Math.max(firstCorner[0], secondCorner[0]);
    var west  = Math.min(firstCorner[1], secondCorner[1]);
    var east  = Math.max(firstCorner[1], secondCorner[1]);

    var bounds = [[south, west], [north, east]];

    if (previewRect) {
      map.removeLayer(previewRect);
    }

    previewRect = L.rectangle(bounds, {
      color: 'orange',
      weight: 2,
      dashArray: '5,5'
    }).addTo(map);
  });

  // Mouse click → set corners
  map.on('click', function(e) {
    if (!firstCorner) {
      // First corner
      firstCorner = [e.latlng.lat, e.latlng.lng];
      return;
    }

    // Second corner
    var secondCorner = [e.latlng.lat, e.latlng.lng];

    var south = Math.min(firstCorner[0], secondCorner[0]);
    var north = Math.max(firstCorner[0], secondCorner[0]);
    var west  = Math.min(firstCorner[1], secondCorner[1]);
    var east  = Math.max(firstCorner[1], secondCorner[1]);

    var bounds = [[south, west], [north, east]];

    if (previewRect) {
      map.removeLayer(previewRect);
      previewRect = null;
    }

    if (finalRect) {
      map.removeLayer(finalRect);
    }

    finalRect = L.rectangle(bounds, {
      color: 'red',
      weight: 3
    }).addTo(map);

    // Skicka bbox till Python: [minLon, minLat, maxLon, maxLat]
    var bbox = [west, south, east, north];

    if (window.pyObj) {
      window.pyObj.receiveBBox(JSON.stringify(bbox));
    }

    firstCorner = null;
  });

</script>

</body>
</html>
"""


