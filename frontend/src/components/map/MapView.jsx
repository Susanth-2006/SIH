import { useEffect, useRef, useState } from 'react'

const MAP_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''

let mapsLoaded = false
let mapsPromise = null

function loadGoogleMaps() {
  if (mapsLoaded) return Promise.resolve()
  if (mapsPromise) return mapsPromise

  mapsPromise = new Promise((resolve, reject) => {
    const existing = document.getElementById('gmap-script')
    if (existing) {
      existing.addEventListener('load', () => resolve())
      return
    }

    const script = document.createElement('script')
    script.id = 'gmap-script'
    script.src = `https://maps.googleapis.com/maps/api/js?key=${MAP_KEY}&v=weekly&libraries=maps,marker`
    script.async = true
    script.addEventListener('load', () => {
      mapsLoaded = true
      resolve()
    })
    script.addEventListener('error', () => reject(new Error('Failed to load Google Maps API')))
    document.head.appendChild(script)
  })

  return mapsPromise
}

const CENTER = { lat: 17.385, lng: 78.4867 }

function getPotholeColor(status) {
  switch (status) {
    case 'PENDING_VERIFICATION': return '#f59e0b'
    case 'VERIFIED': return '#10b981'
    case 'WORK_STARTED': return '#06b6d4'
    case 'WORK_FINISHED': return '#8b5cf6'
    case 'FIXED': return '#22c55e'
    case 'REPAIR_FAILED': return '#dc2626'
    default: return '#f59e0b'
  }
}

function getViolationColor(status) {
  switch (status) {
    case 'AI_VERIFIED': return '#22c55e'
    case 'PENDING_OFFICER': return '#f59e0b'
    case 'OFFICER_VERIFIED': return '#3b82f6'
    default: return '#ef4444'
  }
}

export default function MapView({ incidents, filters, onMarkerClick, height = '100%' }) {
  const mapRef = useRef(null)
  const containerRef = useRef(null)
  const [map, setMap] = useState(null)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    let cancelled = false

    const onAuthFailure = () => {
      if (!cancelled) setLoadError('Google Maps rejected the API key (invalid key, quota exceeded, or billing not enabled).')
    }
    window.addEventListener('gm_authFailure', onAuthFailure)

    loadGoogleMaps()
      .then(() => {
        if (cancelled || !containerRef.current) return
        if (!window.google || !window.google.maps) {
          setLoadError('Google Maps script loaded but the API did not initialize.')
          return
        }
        const newMap = new window.google.maps.Map(containerRef.current, {
          center: CENTER,
          zoom: 14,
          mapTypeControl: true,
          fullscreenControl: false,
          streetViewControl: false,
          zoomControl: true,
        })
        setMap(newMap)
      })
      .catch((e) => {
        if (!cancelled) setLoadError(e.message)
      })
    return () => {
      cancelled = true
      window.removeEventListener('gm_authFailure', onAuthFailure)
    }
  }, [])

  useEffect(() => {
    if (!map) return

    if (!map.markers) map.markers = {}
    const markers = map.markers
    const render = []

    if (filters.showFleet) {
      ;(incidents.fleet_markers || []).forEach((m) => {
        render.push({ key: m.id, type: 'fleet', marker: m })
      })
    }

    if (filters.showPotholes) {
      ;(incidents.pothole_markers || []).forEach((m) => {
        render.push({ key: m.id, type: 'pothole', marker: m })
      })
    }

    if (filters.showViolations) {
      ;(incidents.violation_markers || []).forEach((m) => {
        render.push({ key: m.id, type: 'violation', marker: m })
      })
    }

    const visibleKeys = new Set(render.map((r) => `${r.type}-${r.key}`))

    // Remove markers that should no longer be visible
    Object.keys(markers).forEach((key) => {
      if (!visibleKeys.has(key)) {
        markers[key].setMap(null)
        delete markers[key]
      }
    })

    // Add/update markers
    render.forEach(({ type, key, marker }) => {
      const mapKey = `${type}-${key}`
      const position = { lat: marker.latitude, lng: marker.longitude }

      if (markers[mapKey] && markers[mapKey].type === type) {
        markers[mapKey].setPosition(position)
        return
      }

      let pinColor
      if (type === 'fleet') {
        pinColor = '#2563eb'
      } else if (type === 'pothole') {
        pinColor = getPotholeColor(marker.status)
      } else {
        pinColor = getViolationColor(marker.status)
      }

      const iconUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(
        `<svg xmlns="http://www.w3.org/2000/svg" width="34" height="34" viewBox="0 0 34 34">
          <circle cx="17" cy="17" r="15" fill="${pinColor}" stroke="#ffffff" stroke-width="2"/>
          <text x="17" y="17" font-size="13" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-family="Arial">${type === 'fleet' ? 'B' : type === 'pothole' ? '!' : '!'}</text>
        </svg>`
      )

      try {
        const marker = new window.google.maps.Marker({
          map,
          position,
          title: marker.title,
          icon: { url: iconUrl, scaledSize: new window.google.maps.Size(30, 30), anchor: new window.google.maps.Point(15, 15) },
        })
        marker.addListener('click', () => onMarkerClick(marker))
        marker.type = type
        markers[mapKey] = marker
      } catch (e) {
        const simpleMarker = new window.google.maps.Marker({
          map,
          position,
          title: marker.title,
        })
        simpleMarker.addListener('click', () => onMarkerClick(marker))
        simpleMarker.type = type
        markers[mapKey] = simpleMarker
      }
    })

    return () => {}
  }, [map, incidents, filters, onMarkerClick])

  useEffect(() => {
    if (!map || !filters.showRoutes) {
      if (map && map.routes) {
        map.routes.forEach((r) => r.setMap(null))
        map.routes = []
      }
      return
    }

    if (!map.routes) map.routes = []
    map.routes.forEach((r) => r.setMap(null))
    map.routes = []

    ;(incidents.routes || []).forEach((route) => {
      const coords = route.points.map((p) => ({ lat: p.lat, lng: p.lng }))
      const polyline = new window.google.maps.Polyline({
        map,
        path: coords,
        strokeColor: route.color || '#4285F4',
        strokeOpacity: 0.8,
        strokeWeight: 3,
      })
      map.routes.push(polyline)
    })
  }, [map, incidents.routes, filters.showRoutes])

  if (loadError) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#f8fafc',
          borderRadius: 12,
          flexDirection: 'column',
          gap: 8,
          padding: 24,
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: 36 }}>🗺️</div>
        <div style={{ fontWeight: 600, color: '#dc2626' }}>Map could not be loaded</div>
        <div style={{ fontSize: 12, color: '#64748b', maxWidth: 480 }}>
          {loadError}. Check the Google Maps API key and ensure the Maps JavaScript API is enabled.
        </div>
      </div>
    )
  }

  return <div ref={containerRef} style={{ width: '100%', height }} />
}