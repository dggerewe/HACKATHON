/*****************
 * 🔐 AUTH PROTECTION
 *****************/
if (!sessionStorage.getItem("driver_mobile")) {
  window.location.href = "login.html";
}

/*****************
 * 🗺️ MAP SETUP
 *****************/
let map = L.map("map").setView([12.9716, 77.5946], 12);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: "© OpenStreetMap"
}).addTo(map);

/*****************
 * 📌 GLOBAL STATE
 *****************/
let startCoord = null;
let endCoord = null;
let routesData = [];
let polylines = [];
let activeRoute = 0;

let routeLocked = false;
let bestRouteIndex = 0;

let ambulanceMarker = null;
let gpsWatchId = null;

/*****************
 * 🔍 LOCATION SEARCH (AUTOCOMPLETE)
 *****************/
function search(type) {
  const query = document.getElementById(type).value;
  if (query.length < 3) return;

  fetch(`http://127.0.0.1:5000/geocode?q=${encodeURIComponent(query)}`)
    .then(res => res.json())
    .then(data => {
      const box = document.getElementById(type + "-results");
      box.innerHTML = "";

      data.forEach(place => {
        const div = document.createElement("div");
        div.innerText = place.label;
        div.onclick = () => {
          document.getElementById(type).value = place.label;
          if (type === "start") startCoord = place.coords;
          else endCoord = place.coords;
          box.innerHTML = "";
        };
        box.appendChild(div);
      });
    })
    .catch(err => console.error("Geocode error:", err));
}

/*****************
 * 📍 CURRENT LOCATION
 *****************/
function useCurrentLocation() {
  navigator.geolocation.getCurrentPosition(
    pos => {
      startCoord = [pos.coords.longitude, pos.coords.latitude];
      document.getElementById("start").value = "📍 Current Location";
    },
    () => alert("Location access denied")
  );
}

/*****************
 * 🧠 BEST ROUTE SELECTION
 *****************/
function chooseBestRoute(routes) {
  const rank = { LOW: 1, MEDIUM: 2, HIGH: 3 };
  let best = 0;

  for (let i = 1; i < routes.length; i++) {
    if (rank[routes[i].traffic] < rank[routes[best].traffic]) {
      best = i;
    } else if (
      rank[routes[i].traffic] === rank[routes[best].traffic] &&
      routes[i].duration < routes[best].duration
    ) {
      best = i;
    } else if (
      rank[routes[i].traffic] === rank[routes[best].traffic] &&
      routes[i].duration === routes[best].duration &&
      routes[i].distance < routes[best].distance
    ) {
      best = i;
    }
  }
  return best;
}

/*****************
 * 🚦 GET ROUTES
 *****************/
function getRoutes() {
  if (!startCoord || !endCoord) {
    alert("Please select start and destination");
    return;
  }

  fetch("http://127.0.0.1:5000/routes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start: startCoord, end: endCoord })
  })
    .then(res => res.json())
    .then(data => {
      if (!data.routes || data.routes.length === 0) {
        alert("No routes found");
        return;
      }

      routesData = data.routes;
      polylines.forEach(p => map.removeLayer(p));
      polylines = [];

      bestRouteIndex = chooseBestRoute(routesData);
      activeRoute = bestRouteIndex;
      routeLocked = false;

      const info = document.getElementById("info");
      info.innerHTML = "<h3>🚑 Available Emergency Routes</h3>";

      routesData.forEach((r, i) => {
        const color = i === 0 ? "red" : i === 1 ? "blue" : "green";
        const line = L.polyline(r.coords, { color, weight: 4 }).addTo(map);
        polylines.push(line);

        info.innerHTML += `
          <label>
            <input type="radio" name="route"
              ${i === activeRoute ? "checked" : ""}
              onclick="selectRoute(${i})">
            <strong>Route ${i + 1}</strong> |
            📏 ${r.distance} km |
            ⏱️ ${r.duration} min |
            🚦 ${r.traffic} traffic |
            ⏳ Wait ${r.predicted_wait}s
          </label><br>
        `;
      });

      info.innerHTML += `<br>
        <button onclick="startNavigation()">🚀 Start Emergency Route</button>
      `;

      map.fitBounds(polylines[activeRoute].getBounds());
      selectRoute(activeRoute);
    })
    .catch(err => {
      console.error("Routes error:", err);
      alert("Backend error – check terminal");
    });
}

/*****************
 * 🎯 SELECT ROUTE
 *****************/
function selectRoute(i) {
  activeRoute = i;
  polylines.forEach((p, idx) =>
    p.setStyle({ weight: idx === i ? 7 : 4 })
  );
}

/*****************
 * 📏 DISTANCE CALCULATION
 *****************/
function getDistanceMeters(lat1, lon1, lat2, lon2) {
  const R = 6371000;
  const toRad = deg => deg * Math.PI / 180;

  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) *
    Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) ** 2;

  return 2 * R * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/*****************
 * 🚨 START NAVIGATION (LIVE GPS)
 *****************/
function startNavigation() {
  if (routeLocked) return;

  if (routesData[activeRoute].traffic === "HIGH") {
    alert("⚠️ High traffic detected. Switching to optimal route.");
    activeRoute = bestRouteIndex;
    selectRoute(activeRoute);
  }

  routeLocked = true;

  fetch("http://127.0.0.1:5000/notify-control-room", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      driver_mobile: sessionStorage.getItem("driver_mobile"),
      distance: routesData[activeRoute].distance,
      duration: routesData[activeRoute].duration,
      roads: routesData[activeRoute].roads
    })
  });

  alert("🚨 Emergency Navigation Started");

  const destination = endCoord;

  gpsWatchId = navigator.geolocation.watchPosition(
    pos => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      const currentPos = [lat, lon];

      if (!ambulanceMarker) {
        ambulanceMarker = L.marker(currentPos, {
          icon: L.icon({
            iconUrl: "https://cdn-icons-png.flaticon.com/512/2967/2967350.png",
            iconSize: [40, 40],
            iconAnchor: [20, 20]
          })
        }).addTo(map);
      } else {
        ambulanceMarker.setLatLng(currentPos);
      }

      map.setView(currentPos, 16);

      const distance = getDistanceMeters(
        lat, lon,
        destination[1], destination[0]
      );

      if (distance < 50) {
        navigator.geolocation.clearWatch(gpsWatchId);
        alert("✅ Destination reached. Auto logout.");
        sessionStorage.clear();
        window.location.href = "login.html";
      }
    },
    () => alert("Please enable GPS"),
    { enableHighAccuracy: true }
  );
}
