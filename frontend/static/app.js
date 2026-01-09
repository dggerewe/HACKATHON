const WS_URL = 'ws://localhost:8000/ws';
let ws;
const ambulances = {};
const emergencies = {};
const markers = {};

function initMap() {
  const map = L.map('map').setView([0,0], 2);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
  }).addTo(map);
  return map;
}

const map = initMap();

function connect() {
  ws = new WebSocket(WS_URL);
  const status = document.getElementById('wsStatus');
  ws.onopen = () => { status.textContent = 'connected'; };
  ws.onclose = () => { status.textContent = 'disconnected'; setTimeout(connect, 2000); };
  ws.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.type === 'ambulance:update') updateAmbulance(msg.ambulance);
    if (msg.type === 'emergency:update') updateEmergency(msg.emergency);
    if (msg.type === 'assignment') updateEmergency(msg.emergency);
  };
}

function updateAmbulance(a) {
  ambulances[a.id] = a;
  const el = document.getElementById('amb-' + a.id) || createAmbulanceElement(a);
  el.querySelector('.status').textContent = a.status || '';
  el.querySelector('.pos').textContent = `${a.lat.toFixed(5)}, ${a.lon.toFixed(5)}`;

  // marker
  if (markers['amb-' + a.id]) {
    markers['amb-' + a.id].setLatLng([a.lat, a.lon]);
  } else {
    const m = L.marker([a.lat, a.lon], {title: a.call_sign || a.id}).addTo(map).bindPopup('Ambulance ' + (a.call_sign||a.id));
    markers['amb-' + a.id] = m;
  }
}

function updateEmergency(e) {
  emergencies[e.id] = e;
  const el = document.getElementById('em-' + e.id) || createEmergencyElement(e);
  el.querySelector('.status').textContent = e.status || '';
  el.querySelector('.pos').textContent = `${e.lat.toFixed(5)}, ${e.lon.toFixed(5)}`;
  el.querySelector('.assigned').textContent = e.assigned_ambulance_id || '-';

  if (markers['em-' + e.id]) {
    markers['em-' + e.id].setLatLng([e.lat, e.lon]);
  } else {
    const m = L.circleMarker([e.lat, e.lon], {color: 'red'}).addTo(map).bindPopup('Emergency ' + e.id);
    markers['em-' + e.id] = m;
  }
}

function createAmbulanceElement(a) {
  const list = document.getElementById('ambulanceList');
  const div = document.createElement('div');
  div.className = 'item';
  div.id = 'amb-' + a.id;
  div.innerHTML = `<div><strong>${a.call_sign || a.id}</strong></div><div class="status">${a.status||''}</div><div class="pos">${a.lat}, ${a.lon}</div>`;
  list.appendChild(div);
  return div;
}

function createEmergencyElement(e) {
  const list = document.getElementById('emergencyList');
  const div = document.createElement('div');
  div.className = 'item';
  div.id = 'em-' + e.id;
  div.innerHTML = `<div><strong>${e.type || e.id}</strong></div>
    <div class="status">${e.status||''}</div>
    <div class="pos">${e.lat}, ${e.lon}</div>
    <div>Assigned: <span class="assigned">${e.assigned_ambulance_id || '-'}</span></div>
    <div><select class="assignSelect"></select><button class="assignBtn">Assign</button></div>`;
  list.appendChild(div);

  const select = div.querySelector('.assignSelect');
  const btn = div.querySelector('.assignBtn');
  function refreshOptions() {
    select.innerHTML = '';
    Object.values(ambulances).forEach(a => {
      const opt = document.createElement('option'); opt.value = a.id; opt.textContent = a.call_sign || a.id; select.appendChild(opt);
    });
  }
  refreshOptions();
  btn.onclick = () => {
    const ambulance_id = select.value;
    const payload = { type: 'assignment', emergency_id: e.id, ambulance_id };
    ws.send(JSON.stringify(payload));
  };
  return div;
}

connect();

// fetch initial state via REST
fetch('http://localhost:8000/api/ambulances').then(r=>r.json()).then(list=>list.forEach(updateAmbulance));
fetch('http://localhost:8000/api/emergencies').then(r=>r.json()).then(list=>list.forEach(updateEmergency));
