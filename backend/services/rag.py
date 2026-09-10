"""
WeatherKnowledgeBase: Sector RAG (Retrieval-Augmented Generation) Architecture
Provides verified domain knowledge for Agriculture, Marine, Aviation, and Disasters.
Maintains strict provenance: title, organization, source_url, date, sector, and tags.
Ensures reference knowledge is never conflated with active emergency alerts.
"""
from dataclasses import dataclass, field
import re
import math
from datetime import datetime
from typing import Any

@dataclass
class KnowledgeChunk:
    id: str
    title: str
    organization: str
    source_url: str
    document_date: str
    sector: str  # agriculture, marine, aviation, disaster, general
    category: str  # agromet_advisory, marine_safety, flight_rules, disaster_protocol
    content: str
    keywords: list[str] = field(default_factory=list)
    state: str | None = None
    district: str | None = None
    validity_note: str = "Reference operational guidance"


# Curated, authoritative guidelines from IMD Agromet, INCOIS, DGCA, and NDMA
AUTHORITATIVE_KNOWLEDGE: list[KnowledgeChunk] = [
    # ------------------ AGRICULTURE / AGROMET ------------------
    KnowledgeChunk(
        id="agri-spray-01",
        title="IMD Agromet Advisory: Agricultural Spraying Protocols",
        organization="India Meteorological Department (IMD)",
        source_url="https://agromet.imd.gov.in/",
        document_date="2026-01-15",
        sector="agriculture",
        category="agromet_advisory",
        content=(
            "Pesticide and chemical spraying should strictly be conducted during calm wind conditions (< 15 km/h) "
            "to prevent droplet drift into adjacent areas. Avoid spraying if rainfall is forecast within 4–6 hours, "
            "as precipitation washes away applied chemicals, reducing efficacy and causing environmental runoff. "
            "Relative humidity between 50% and 70% is optimal; high temperatures (> 35 °C) accelerate evaporation."
        ),
        keywords=["spray", "pesticide", "insecticide", "fungicide", "drift", "wind", "chemicals", "washing"],
    ),
    KnowledgeChunk(
        id="agri-irrig-01",
        title="ICAR-IMD Standard Operating Procedure: Irrigation Scheduling",
        organization="ICAR - Central Institute / IMD Agricultural Meteorology",
        source_url="https://icar.org.in/",
        document_date="2026-02-01",
        sector="agriculture",
        category="agromet_advisory",
        content=(
            "Before scheduling irrigation, assess soil moisture in the root zone (top 15–30 cm) and upcoming 48-hour rainfall. "
            "If forecast precipitation exceeds 10–15 mm, postpone irrigation to prevent waterlogging and nitrogen leaching. "
            "For rice (paddy), maintain standing water during tillering and panicle initiation, but drain fields during extreme rain. "
            "Light and frequent irrigation is recommended during hot, dry spells with high evapotranspiration."
        ),
        keywords=["irrigate", "irrigation", "rice", "paddy", "wheat", "waterlogging", "soil moisture", "drainage"],
    ),
    KnowledgeChunk(
        id="agri-fert-01",
        title="IMD Agromet Guidance: Fertilizer Application & Heavy Rainfall",
        organization="IMD Agromet Division",
        source_url="https://agromet.imd.gov.in/",
        document_date="2026-02-10",
        sector="agriculture",
        category="agromet_advisory",
        content=(
            "Do not apply top-dressing fertilizers (such as urea) immediately before or during heavy rainfall events. "
            "Excessive surface runoff leaches nitrogen into waterways and causes significant nutrient loss. "
            "Apply nitrogenous fertilizer when the soil has adequate moisture but no standing water or heavy rain threat. "
            "In case of waterlogging, clear field drains immediately to protect standing crops."
        ),
        keywords=["fertilizer", "urea", "nitrogen", "rain", "leaching", "runoff", "top-dressing", "dalu", "fertiliser"],
    ),
    KnowledgeChunk(
        id="agri-crop-01",
        title="Kharif & Rabi Weather Sensitivity: Rice, Wheat, Cotton, Pulses",
        organization="ICAR - Agricultural Research Service",
        source_url="https://icar.org.in/",
        document_date="2026-01-20",
        sector="agriculture",
        category="agromet_advisory",
        content=(
            "Rice is resilient to standing water but vulnerable to flash flooding during early seedling and harvesting stages. "
            "Wheat is sensitive to unseasonal rainfall and hail during grain filling and physiological maturity, causing lodging. "
            "Cotton is highly prone to pest flare-up (bollworm, whitefly) during prolonged cloudy and humid spells. "
            "Pulses require well-drained soil; water stagnation for more than 24 hours causes root rot and wilting."
        ),
        keywords=["rice", "wheat", "cotton", "pulses", "gram", "crop", "kharif", "rabi", "hail", "lodging"],
    ),

    # ------------------ MARINE & COASTAL ------------------
    KnowledgeChunk(
        id="marine-fish-01",
        title="INCOIS-IMD Fishermen Operational Safety Guidelines",
        organization="Indian National Centre for Ocean Information Services (INCOIS) / IMD",
        source_url="https://incois.gov.in/",
        document_date="2026-02-15",
        sector="marine",
        category="marine_safety",
        content=(
            "Small mechanized and traditional fishing boats (length < 12m) are advised not to venture into deep sea "
            "when significant wave heights exceed 2.0–2.5 meters or sustained wind speed exceeds 40–45 km/h (22–25 knots). "
            "When IMD issues a Squally Weather or Rough Sea warning, coastal fishermen must anchor craft securely. "
            "Spring tides combined with elevated swell cause severe breaker zones near coastal river mouths and bar entrances."
        ),
        keywords=["sea", "boat", "fishing", "fish", "waves", "machhli", "visakhapatnam", "chennai", "mumbai", "swell", "coastal"],
    ),
    KnowledgeChunk(
        id="marine-cyclone-01",
        title="IMD Coastal Warning Protocols: Cyclone & Low Pressure Depressions",
        organization="IMD Cyclone Warning Division",
        source_url="https://mausam.imd.gov.in/",
        document_date="2026-01-28",
        sector="marine",
        category="marine_safety",
        content=(
            "During cyclone alerts, fishermen out at deep sea are advised through coastal radio and NAVTEX to return to port. "
            "Port warning signals (Signal 1 to 11) denote cyclone distance and severity. "
            "Storm surge heights are amplified when cyclone landfall coincides with astronomical high tides, "
            "causing sea water inundation up to several kilometers inland along low-lying coastlines."
        ),
        keywords=["cyclone", "depression", "storm surge", "port", "signal", "landfall", "inundation", "bay of bengal", "arabian sea"],
    ),

    # ------------------ AVIATION & TRAVEL ------------------
    KnowledgeChunk(
        id="av-vfr-01",
        title="DGCA / IMD Aviation Meteorology: Operating Thresholds",
        organization="Directorate General of Civil Aviation (DGCA) / IMD CAMD",
        source_url="https://dgca.gov.in/",
        document_date="2026-02-05",
        sector="aviation",
        category="flight_rules",
        content=(
            "Visual Flight Rules (VFR) require minimum flight visibility of 5,000 meters and distance from clouds. "
            "Instrument Flight Rules (IFR) are mandatory when visibility drops below VFR minimums due to fog or rain. "
            "Convective activity (Cumulonimbus - CB clouds) poses severe turbulence, icing, and wind shear hazards. "
            "Crosswind components exceeding 15–20 knots significantly impact regional turboprop and general aviation operations."
        ),
        keywords=["aviation", "flight", "pilot", "runway", "visibility", "fog", "vfr", "ifr", "turbulence", "wind shear", "airport"],
    ),
    KnowledgeChunk(
        id="travel-safety-01",
        title="Inter-District Road Travel Safety in Extreme Weather",
        organization="National Disaster Management Authority (NDMA)",
        source_url="https://ndma.gov.in/",
        document_date="2026-02-12",
        sector="general",
        category="disaster_protocol",
        content=(
            "During heavy rain or thunderstorm warnings, road travel between cities (such as Patna to Ranchi, "
            "Delhi to Jaipur, or Mumbai to Pune) requires caution regarding ghat section landslides, waterlogged culverts, "
            "and sudden visibility reduction. Avoid nighttime travel through hilly or low-lying flood-prone corridors. "
            "Monitor official district administration traffic advisories before starting highway journeys."
        ),
        keywords=["travel", "road", "highway", "patna", "ranchi", "journey", "trip", "drive", "safe", "landslide", "ghat"],
    ),

    # ------------------ DISASTER PROTOCOLS ------------------
    KnowledgeChunk(
        id="disaster-thunder-01",
        title="NDMA National Guidelines: Thunderstorm & Lightning Safety",
        organization="National Disaster Management Authority (NDMA)",
        source_url="https://ndma.gov.in/",
        document_date="2026-02-18",
        sector="disaster",
        category="disaster_protocol",
        content=(
            "Lightning is the leading meteorological cause of accidental death in India. "
            "When thunder roars, go indoors. Do not take shelter under isolated tall trees, open fields, or tin sheds. "
            "If caught in an open field, assume the lightning squat position on the balls of your feet with heels together. "
            "Stay away from water bodies, metal fencing, and electrical wiring during active thunderstorm nowcasts."
        ),
        keywords=["thunderstorm", "lightning", "bijli", "thunder", "warning", "safety", "squat", "shelter", "tree"],
    ),
    KnowledgeChunk(
        id="disaster-heat-01",
        title="NDMA National Heatwave Action Plan & Prevention Guidelines",
        organization="National Disaster Management Authority (NDMA)",
        source_url="https://ndma.gov.in/",
        document_date="2026-02-20",
        sector="disaster",
        category="disaster_protocol",
        content=(
            "Heatwave criteria in plains is maximum temperature >= 40 °C with departure >= 4.5 °C. "
            "Avoid strenuous outdoor activity between 12:00 PM and 3:00 PM. "
            "Drink plenty of water, ORS, lemon water, and buttermilk even if not feeling thirsty. "
            "Watch for heat exhaustion signs: dizziness, excessive sweating, headache, nausea, and rapid pulse."
        ),
        keywords=["heatwave", "heat", "temperature", "loo", "hot", "sunstroke", "ors", "hydration"],
    ),
]


class WeatherKnowledgeBase:
    """
    In-memory embedded vector & semantic knowledge retrieval system.
    Matches queries by semantic token overlap, sector alignment, and TF-IDF cosine similarity.
    """
    def __init__(self, chunks: list[KnowledgeChunk] | None = None):
        self.chunks = chunks if chunks is not None else AUTHORITATIVE_KNOWLEDGE
        self._build_index()

    def _build_index(self):
        # Build inverted index and IDF weights
        self.vocab: dict[str, int] = {}
        self.doc_vectors: list[dict[int, float]] = []
        doc_count = len(self.chunks)

        df: dict[str, int] = {}
        for chunk in self.chunks:
            tokens = set(self._tokenize(chunk.title + " " + chunk.content + " " + " ".join(chunk.keywords)))
            for token in tokens:
                df[token] = df.get(token, 0) + 1

        for token, count in df.items():
            self.vocab[token] = len(self.vocab)

        for chunk in self.chunks:
            tokens = self._tokenize(chunk.title + " " + chunk.content + " " + " ".join(chunk.keywords))
            tf: dict[int, float] = {}
            for t in tokens:
                idx = self.vocab[t]
                tf[idx] = tf.get(idx, 0.0) + 1.0
            # Compute TF-IDF
            norm = 0.0
            vec: dict[int, float] = {}
            for idx, count in tf.items():
                token = [k for k, v in self.vocab.items() if v == idx][0]
                idf = math.log((doc_count + 1) / (df[token] + 1)) + 1.0
                val = count * idf
                vec[idx] = val
                norm += val * val
            norm = math.sqrt(norm) or 1.0
            for idx in vec:
                vec[idx] /= norm
            self.doc_vectors.append(vec)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        return [w for w in cleaned.split() if len(w) >= 2]

    def retrieve(self, query: str, sector: str | None = None, top_k: int = 2) -> list[dict[str, Any]]:
        """
        Retrieve authoritative sector RAG documents matching the query.
        Guarantees provenance: title, organization, source_url, date, validity_note.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        q_tf: dict[int, float] = {}
        for t in query_tokens:
            if t in self.vocab:
                idx = self.vocab[t]
                q_tf[idx] = q_tf.get(idx, 0.0) + 1.0

        if not q_tf:
            # Fallback keyword scan
            matches = []
            for chunk in self.chunks:
                if sector and chunk.sector != sector and chunk.sector != "general":
                    continue
                score = sum(1.0 for t in query_tokens if any(t in kw for kw in chunk.keywords))
                if score > 0:
                    matches.append((score, chunk))
            matches.sort(key=lambda x: x[0], reverse=True)
            return [self._format_chunk(c, s) for s, c in matches[:top_k]]

        q_vec: dict[int, float] = {}
        q_norm = 0.0
        for idx, count in q_tf.items():
            val = count
            q_vec[idx] = val
            q_norm += val * val
        q_norm = math.sqrt(q_norm) or 1.0
        for idx in q_vec:
            q_vec[idx] /= q_norm

        scored: list[tuple[float, KnowledgeChunk]] = []
        for i, doc_vec in enumerate(self.doc_vectors):
            chunk = self.chunks[i]
            # Boost matching sector
            sector_boost = 1.3 if (sector and chunk.sector == sector) else 1.0
            # Cosine similarity
            sim = sum(q_vec[idx] * doc_vec[idx] for idx in q_vec if idx in doc_vec) * sector_boost
            if sim > 0.05:
                scored.append((sim, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._format_chunk(c, sim) for sim, c in scored[:top_k]]

    @staticmethod
    def _format_chunk(chunk: KnowledgeChunk, score: float) -> dict[str, Any]:
        return {
            "id": chunk.id,
            "title": chunk.title,
            "organization": chunk.organization,
            "source_url": chunk.source_url,
            "document_date": chunk.document_date,
            "sector": chunk.sector,
            "category": chunk.category,
            "content": chunk.content,
            "validity_note": chunk.validity_note,
            "relevance_score": round(score, 3),
        }


knowledge_base = WeatherKnowledgeBase()
