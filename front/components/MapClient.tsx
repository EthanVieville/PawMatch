'use client'

import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import Link from 'next/link'

export interface Refuge {
  name: string
  source: string
  lat: number
  lng: number
  animal_count: number
  thumbnails: string[]
}

function pawIcon(count: number) {
  return L.divIcon({
    className: '',
    html: `
      <div style="position:relative;display:inline-flex;align-items:center;justify-content:center;cursor:pointer">
        <img src="/pawmatch-icone-patte.svg"
          style="width:42px;height:42px;filter:drop-shadow(0 3px 8px rgba(0,0,0,0.45));" />
        <span style="
          position:absolute;top:-5px;right:-6px;
          background:#B5501A;color:white;
          font-size:10px;font-weight:700;
          min-width:18px;height:18px;border-radius:9px;padding:0 3px;
          display:flex;align-items:center;justify-content:center;
          border:2px solid white;box-sizing:border-box;
          font-family:system-ui,sans-serif;
        ">${count > 99 ? '99+' : count}</span>
      </div>`,
    iconSize: [42, 42],
    iconAnchor: [21, 42],
    popupAnchor: [0, -46],
  })
}

export default function MapClient({ refuges }: { refuges: Refuge[] }) {
  return (
    <MapContainer
      center={[46.5, 2.3]}
      zoom={6}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
      />

      {refuges.map(r => (
        <Marker key={r.name} position={[r.lat, r.lng]} icon={pawIcon(r.animal_count)}>
          <Popup maxWidth={260} className="pawmatch-popup">
            <div style={{ fontFamily: 'system-ui, sans-serif', minWidth: 220 }}>

              {/* Nom du refuge */}
              <div style={{ fontWeight: 700, fontSize: 14, color: '#1C1C10', marginBottom: 4 }}>
                {r.name}
              </div>

              {/* Badge animaux */}
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                background: '#F0EAD6', borderRadius: 99, padding: '2px 10px',
                fontSize: 12, color: '#6B6250', marginBottom: 10,
              }}>
                🐾 <strong style={{ color: '#3D4A2E' }}>{r.animal_count}</strong>
                &nbsp;animal{r.animal_count > 1 ? 'ux' : ''} disponible{r.animal_count > 1 ? 's' : ''}
              </div>

              {/* Miniatures */}
              {r.thumbnails.length > 0 && (
                <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
                  {r.thumbnails.map((url, i) => (
                    <img
                      key={i}
                      src={url}
                      alt=""
                      style={{
                        width: 64, height: 64, objectFit: 'cover',
                        borderRadius: 8, border: '1px solid #C8B99A',
                      }}
                    />
                  ))}
                </div>
              )}

              {/* Lien */}
              <Link
                href={`/animals?refuge=${encodeURIComponent(r.name)}`}
                style={{
                  display: 'block', textAlign: 'center',
                  background: '#B5501A', color: 'white',
                  borderRadius: 8, padding: '6px 0',
                  fontSize: 12, fontWeight: 700,
                  textDecoration: 'none',
                  letterSpacing: '0.03em',
                }}
              >
                Voir les animaux →
              </Link>
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
