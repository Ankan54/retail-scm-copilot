import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { T, fmt } from "./api";
import { CATEGORY_LABELS } from "./api";

const HEALTH_COLORS = {
    healthy: T.green,
    "at-risk": T.orange,
    critical: T.red,
};

const CAT_RADIUS = { A: 14, B: 11, C: 9 };

export default function LeafletMap({ dealers, filters }) {
    const filtered = dealers.filter(d => {
        if (filters.atRiskOnly && !["at-risk", "critical"].includes(d.health)) return false;
        if (filters.category !== "All" && d.category !== filters.category) return false;
        return true;
    });

    return (
        <MapContainer
            center={[28.63, 77.22]}
            zoom={11}
            style={{ height: "100%", width: "100%", borderRadius: 12, zIndex: 1 }}
            scrollWheelZoom={true}
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {filtered.map(d => (
                <CircleMarker
                    key={d.id}
                    center={[d.lat, d.lng]}
                    radius={CAT_RADIUS[d.category] || 9}
                    pathOptions={{
                        color: "#fff",
                        weight: 2.5,
                        fillColor: HEALTH_COLORS[d.health] || T.teal,
                        fillOpacity: 0.92,
                    }}
                >
                    <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                        <div style={{ fontFamily: "'DM Sans',system-ui", minWidth: 180, fontSize: 12 }}>
                            <div style={{ fontWeight: 700, color: T.heading, marginBottom: 6 }}>{d.name}</div>
                            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "3px 10px", color: T.text }}>
                                <span style={{ color: T.textMuted }}>Category</span>
                                <span style={{ fontWeight: 600 }}>{CATEGORY_LABELS[d.category]} ({d.category})</span>
                                <span style={{ color: T.textMuted }}>Status</span>
                                <span style={{ fontWeight: 600, color: HEALTH_COLORS[d.health] }}>{d.health}</span>
                                <span style={{ color: T.textMuted }}>Revenue</span>
                                <span style={{ fontWeight: 600, color: T.green }}>{fmt(d.revenue)}</span>
                                <span style={{ color: T.textMuted }}>Outstanding</span>
                                <span style={{ fontWeight: 600, color: d.outstanding > 100000 ? T.red : T.orange }}>{fmt(d.outstanding)}</span>
                                <span style={{ color: T.textMuted }}>Last Visit</span>
                                <span>{d.last_visit}</span>
                                <span style={{ color: T.textMuted }}>Sales Rep</span>
                                <span>{d.sales_rep}</span>
                            </div>
                        </div>
                    </Tooltip>
                </CircleMarker>
            ))}
        </MapContainer>
    );
}
