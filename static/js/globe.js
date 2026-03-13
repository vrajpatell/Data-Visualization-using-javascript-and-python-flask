(() => {
  const globeContainer = document.getElementById('globeViz');
  const statusBanner = document.getElementById('statusBanner');
  const stats = document.getElementById('stats');
  const magMinInput = document.getElementById('magMin');
  const autoRefreshInput = document.getElementById('autoRefresh');
  const autoRotateInput = document.getElementById('autoRotate');
  const recentHoursInput = document.getElementById('recentHours');
  const colorModeInput = document.getElementById('colorMode');
  const maxPointsInput = document.getElementById('maxPoints');
  const heightScaleInput = document.getElementById('heightScale');
  const refreshButton = document.getElementById('refreshButton');

  const REFRESH_INTERVAL_MS = 120000;
  let refreshTimer = null;
  let rotateTimer = null;

  const world = Globe()(globeContainer)
    .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
    .backgroundImageUrl('https://unpkg.com/three-globe/example/img/night-sky.png')
    .showAtmosphere(true)
    .atmosphereColor('#7dd3fc')
    .atmosphereAltitude(0.18)
    .pointAltitude((d) => d.altitude)
    .pointRadius((d) => d.radius)
    .pointColor((d) => d.color)
    .pointLabel((d) => d.label)
    .onPointClick((point) => {
      world.pointOfView({ lat: point.lat, lng: point.lng, altitude: 1.6 }, 1200);
    })
    .pointsTransitionDuration(500);

  function magnitudeColor(mag) {
    if (mag >= 6) return '#ef4444';
    if (mag >= 4) return '#f97316';
    if (mag >= 2) return '#f59e0b';
    return '#10b981';
  }

  function depthColor(depth) {
    if (depth >= 150) return '#7c3aed';
    if (depth >= 70) return '#2563eb';
    if (depth >= 30) return '#0ea5e9';
    return '#22c55e';
  }

  function isRecent(timeMs, hours) {
    if (!hours || hours <= 0 || !timeMs) return true;
    const windowMs = hours * 60 * 60 * 1000;
    return (Date.now() - timeMs) <= windowMs;
  }

  function toPoint(quake, colorMode, heightScale) {
    const magnitude = Number.isFinite(quake.magnitude) ? quake.magnitude : 0;
    const lat = Number.isFinite(quake.latitude) ? quake.latitude : 0;
    const lng = Number.isFinite(quake.longitude) ? quake.longitude : 0;
    const depth = Number.isFinite(quake.depth) ? quake.depth : 0;
    const place = quake.place || 'Unknown location';
    const timeMs = Number.isFinite(quake.time_ms) ? quake.time_ms : 0;
    const time = timeMs ? new Date(timeMs).toLocaleString() : 'Unknown time';

    return {
      id: quake.id || `quake-${lat}-${lng}-${timeMs}`,
      lat,
      lng,
      magnitude,
      depth,
      timeMs,
      radius: 0.05 + Math.max(magnitude, 0) * 0.045,
      altitude: (0.01 + Math.max(magnitude, 0) * 0.025) * heightScale,
      color: colorMode === 'depth' ? depthColor(depth) : magnitudeColor(magnitude),
      label: `<div><strong>${place}</strong><br/>Magnitude: ${magnitude.toFixed(1)}<br/>Depth: ${depth.toFixed(1)} km<br/>Time: ${time}</div>`
    };
  }

  function updateStatus(message, isError = false) {
    statusBanner.textContent = message;
    statusBanner.style.borderColor = isError ? '#ef4444' : '#334155';
  }

  async function fetchEarthquakes(forceRefresh = false) {
    const magMin = parseFloat(magMinInput.value);
    const recentHours = parseFloat(recentHoursInput.value);
    const maxPoints = parseInt(maxPointsInput.value, 10);
    const colorMode = colorModeInput.value;
    const heightScale = parseFloat(heightScaleInput.value) || 1;

    const params = new URLSearchParams({
      mag_min: Number.isFinite(magMin) ? String(magMin) : '0',
      mag_max: '10',
      refresh: forceRefresh ? '1' : '0'
    });

    updateStatus('Loading earthquake data...');

    try {
      const response = await fetch(`/api/earthquakes?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`API error ${response.status}`);
      }

      const payload = await response.json();
      const rows = Array.isArray(payload.data) ? payload.data : [];
      const filteredRows = rows.filter((row) => isRecent(row.time_ms, recentHours));
      const cappedRows = Number.isFinite(maxPoints) ? filteredRows.slice(0, maxPoints) : filteredRows;
      const points = cappedRows.map((row) => toPoint(row, colorMode, heightScale));

      world.pointsData(points);

      if (points.length === 0) {
        updateStatus('No earthquakes match your current filters.');
      } else {
        updateStatus('Data loaded. Hover points for details; click a point to focus.');
      }

      const lastRefresh = payload.meta?.last_refresh_epoch
        ? new Date(payload.meta.last_refresh_epoch * 1000).toLocaleString()
        : 'n/a';
      const source = payload.meta?.source || 'unknown';
      stats.textContent = `Displayed: ${points.length}/${rows.length} | Source: ${source} | Last updated: ${lastRefresh}`;
    } catch (err) {
      world.pointsData([]);
      stats.textContent = 'Displayed: 0';
      updateStatus('Unable to load earthquake data right now. Please retry.', true);
      console.error(err);
    }
  }

  function setAutoRefresh(enabled) {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
    if (enabled) {
      refreshTimer = setInterval(() => fetchEarthquakes(false), REFRESH_INTERVAL_MS);
    }
  }

  function setAutoRotate(enabled) {
    if (rotateTimer) {
      clearInterval(rotateTimer);
      rotateTimer = null;
    }
    if (enabled) {
      rotateTimer = setInterval(() => {
        const pov = world.pointOfView();
        world.pointOfView({ lat: pov.lat, lng: pov.lng + 0.18, altitude: pov.altitude }, 0);
      }, 40);
    }
  }

  refreshButton.addEventListener('click', () => fetchEarthquakes(true));
  [magMinInput, recentHoursInput, colorModeInput, maxPointsInput, heightScaleInput]
    .forEach((el) => el.addEventListener('change', () => fetchEarthquakes(false)));
  autoRefreshInput.addEventListener('change', () => setAutoRefresh(autoRefreshInput.checked));
  autoRotateInput.addEventListener('change', () => setAutoRotate(autoRotateInput.checked));

  setAutoRefresh(autoRefreshInput.checked);
  setAutoRotate(autoRotateInput.checked);
  fetchEarthquakes(false);
})();
