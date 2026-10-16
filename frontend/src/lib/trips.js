/**
 * Dummy trip history for the RydeResolve demo.
 * Trips are stored in localStorage per identity so riders/drivers see
 * a realistic history list. They are purely synthetic — no real trips,
 * GPS, or payments are connected.
 */

const STORAGE_KEY = 'ryderesolve_trips_v1';

const SINGAPORE_AREAS = [
  'Orchard Road', 'Marina Bay', 'Tampines', 'Jurong East', 'Ang Mo Kio',
  'Bedok', 'Clementi', 'Bishan', 'Paya Lebar', 'Holland Village',
  'Sentosa', 'Changi Airport', 'Sengkang', 'Punggol', 'Woodlands',
  'Yishun', 'Serangoon', 'Kallang', 'Geylang', 'Novena',
];

const DRIVERS = [
  { name: 'Ahmad K.', vehicle: 'Toyota Corolla · SGY1234A', rating: 4.7 },
  { name: 'Sarah T.', vehicle: 'Honda Vezel · SGY5678B', rating: 4.9 },
  { name: 'Raj P.', vehicle: 'Hyundai Avante · SGY9012C', rating: 4.6 },
  { name: 'Li Wei', vehicle: 'Mazda 3 · SGY3456D', rating: 4.8 },
  { name: 'Fatimah R.', vehicle: 'Kia Cerato · SGY7890E', rating: 4.9 },
];

function rand(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function randBetween(min, max) {
  return Math.random() * (max - min) + min;
}

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function fmtDate(d) {
  return d.toISOString().slice(0, 10);
}

function fmtTime(d) {
  return d.toTimeString().slice(0, 5);
}

function generateTrips(identityId, count = 6) {
  const trips = [];
  const now = new Date();
  for (let i = 0; i < count; i++) {
    const daysAgo = i * randInt(1, 5) + randInt(0, 2);
    const date = new Date(now);
    date.setDate(date.getDate() - daysAgo);
    date.setHours(randInt(7, 23), randInt(0, 59));

    let pickup = rand(SINGAPORE_AREAS);
    let dropoff = rand(SINGAPORE_AREAS);
    while (dropoff === pickup) dropoff = rand(SINGAPORE_AREAS);

    const distanceKm = Number(randBetween(3, 22).toFixed(1));
    const durationMin = Math.max(8, Math.round(distanceKm * randBetween(2, 4.5)));
    const fare = Number((distanceKm * randBetween(1.1, 1.8) + randBetween(2.5, 5)).toFixed(2));
    const driver = rand(DRIVERS);

    // Synthetic lat/lng offsets around Singapore centre-ish (visual only)
    const baseLat = 1.35;
    const baseLng = 103.82;
    const pickupLat = baseLat + randBetween(-0.06, 0.06);
    const pickupLng = baseLng + randBetween(-0.08, 0.08);
    const dropoffLat = baseLat + randBetween(-0.06, 0.06);
    const dropoffLng = baseLng + randBetween(-0.08, 0.08);

    trips.push({
      trip_id: `TRIP-${date.toISOString().slice(0, 10).replace(/-/g, '')}-${String.fromCharCode(65 + i)}${randInt(100, 999)}`,
      date: fmtDate(date),
      time: fmtTime(date),
      pickup_location: pickup,
      dropoff_location: dropoff,
      pickup_lat: pickupLat,
      pickup_lng: pickupLng,
      dropoff_lat: dropoffLat,
      dropoff_lng: dropoffLng,
      distance_km: distanceKm,
      duration_min: durationMin,
      fare,
      currency: 'SGD',
      driver_name: driver.name,
      vehicle_info: driver.vehicle,
      driver_rating: driver.rating,
      status: 'completed',
      payment_method: rand(['Credit card', 'Apple Pay', 'Google Pay', 'PayNow']),
      identity_id: identityId,
    });
  }
  // Sort newest first
  return trips.sort((a, b) => `${b.date}T${b.time}`.localeCompare(`${a.date}T${a.time}`));
}

function loadAll() {
  if (typeof window === 'undefined') return {};
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function saveAll(all) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
}

export function getTrips(identityId) {
  const all = loadAll();
  if (!all[identityId]) {
    all[identityId] = generateTrips(identityId);
    saveAll(all);
  }
  return all[identityId];
}

export function addTrip(identityId, trip) {
  const all = loadAll();
  const list = all[identityId] || [];
  list.unshift({ ...trip, identity_id: identityId });
  all[identityId] = list;
  saveAll(all);
  return list;
}

export function findTrip(identityId, tripId) {
  return getTrips(identityId).find((t) => t.trip_id === tripId);
}

export function resetTrips(identityId) {
  const all = loadAll();
  all[identityId] = generateTrips(identityId);
  saveAll(all);
  return all[identityId];
}

export function formatTripDateTime(trip) {
  return `${trip.date} · ${trip.time}`;
}

export function formatFare(trip) {
  return `${trip.currency || 'SGD'} ${trip.fare.toFixed(2)}`;
}
