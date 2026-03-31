import React, { useEffect, useRef } from 'react'

const RISK_COLORS = {
  CRITICAL: '#c0392b',
  HIGH: '#d35400',
  MODERATE: '#b7950b',
  LOW: '#1e8449',
}

function getRiskColor(zone) {
  if (zone.risk_level) return RISK_COLORS[zone.risk_level] || '#8896a4'
  // Fallback: estimate from risk_score
  if (zone.risk_score >= 75) return RISK_COLORS.CRITICAL
  if (zone.risk_score >= 55) return RISK_COLORS.HIGH
  if (zone.risk_score >= 35) return RISK_COLORS.MODERATE
  return RISK_COLORS.LOW
}

export default function RegionMap({ region, zones = [], height = 300 }) {
  const mapRef = useRef(null)
  const mapInstance = useRef(null)
  const markersRef = useRef([])

  useEffect(() => {
    if (!region || mapInstance.current) return

    // Dynamic leaflet import
    import('leaflet').then(L => {
      const map = L.default.map(mapRef.current, {
        center: [region.lat || 28.6, region.lon || 77.2],
        zoom: 10,
        zoomControl: true,
        scrollWheelZoom: false,
        attributionControl: false
      })

      L.default.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: 'CartoDB',
        maxZoom: 19
      }).addTo(map)

      mapInstance.current = map
    })

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove()
        mapInstance.current = null
      }
    }
  }, [region?.id])

  // Update markers when zones change
  useEffect(() => {
    if (!mapInstance.current || !zones.length) return

    import('leaflet').then(L => {
      // Clear existing markers
      markersRef.current.forEach(m => m.remove())
      markersRef.current = []

      zones.forEach(zone => {
        if (!zone.lat || !zone.lon) return

        const color = getRiskColor(zone)
        const radius = Math.max(300, Math.sqrt(zone.population || 100000) * 2)

        const circle = L.default.circle([zone.lat, zone.lon], {
          radius,
          color,
          fillColor: color,
          fillOpacity: 0.3,
          weight: 2,
          opacity: 0.8
        }).addTo(mapInstance.current)

        circle.bindPopup(`
          <div style="font-family: 'IBM Plex Sans', sans-serif; padding: 4px; min-width: 180px;">
            <div style="font-weight: 700; font-size: 13px; margin-bottom: 6px; color: #0f1923;">${zone.name}</div>
            <div style="font-size: 11px; color: #4a5568; margin-bottom: 2px;">Population: <strong>${(zone.population || 0).toLocaleString()}</strong></div>
            <div style="font-size: 11px; color: #4a5568; margin-bottom: 2px;">Density: <strong>${(zone.population_density || 0).toLocaleString()} /km²</strong></div>
            <div style="font-size: 11px; color: #4a5568; margin-bottom: 4px;">Active Cases: <strong>${(zone.current_cases || 0).toLocaleString()}</strong></div>
            ${zone.risk_score ? `<div style="font-size: 11px; color: ${color}; font-weight: 700;">Risk: ${zone.risk_level} (${zone.risk_score}/100)</div>` : ''}
          </div>
        `, { maxWidth: 220 })

        markersRef.current.push(circle)
      })
    })
  }, [zones])

  return (
    <div
      ref={mapRef}
      style={{ width: '100%', height, background: '#e8edf2' }}
    />
  )
}
