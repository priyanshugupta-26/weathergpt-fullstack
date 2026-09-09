"""Validity-aware alert fusion and geographic matching; no inferred boundaries."""
from datetime import datetime, timezone
from defusedxml import ElementTree
from ..providers.imd import distance


def active(alert, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        start = datetime.fromisoformat((alert.get("effective") or alert.get("timestamp") or "").replace("Z", "+00:00"))
        end = datetime.fromisoformat((alert.get("expires") or "").replace("Z", "+00:00"))
        return start <= now < end
    except (ValueError, TypeError):
        return False


def inside(lat, lon, polygon):
    hit = False
    for i, (x, y) in enumerate(polygon):
        px, py = polygon[i-1]
        if ((y > lat) != (py > lat)) and lon < (px-x)*(lat-y)/(py-y)+x:
            hit = not hit
    return hit


class AlertFusionEngine:
    @staticmethod
    def matches(alert, location):
        district = str(location.get("district") or location.get("name") or "").replace("_", " ").casefold()
        if district and district == str(alert.get("district") or alert.get("location") or "").replace("_", " ").casefold():
            return True
        lat, lon = location.get("latitude"), location.get("longitude")
        if lat is None or lon is None:
            return False
        for polygon in alert.get("polygons", []):
            if inside(lat, lon, polygon):
                return True
        for circle in alert.get("circles", []):
            if distance(lat, lon, circle[0], circle[1]) <= circle[2] + location.get("radius_km", 0):
                return True
        if alert.get("latitude") is not None and alert.get("longitude") is not None:
            return distance(lat, lon, alert["latitude"], alert["longitude"]) <= location.get("radius_km", 25)
        return False

    @staticmethod
    def fuse(*groups):
        unique = {}
        for group in groups:
            for item in group:
                if not active(item):
                    continue
                key = item["id"]
                if key not in unique or item.get("priority", 5) < unique[key].get("priority", 5):
                    unique[key] = item
        rank = {"SEVERE": 0, "WARNING": 1, "WATCH": 2, "INFO": 3, "UNKNOWN": 4}
        return sorted(unique.values(), key=lambda a: (a.get("priority", 5), rank.get(a.get("severity"), 4)))


class CAPAlertParser:
    namespace = {"c": "urn:oasis:names:tc:emergency:cap:1.2"}

    def parse(self, xml):
        if len(xml) > 2_000_000:
            raise ValueError("CAP payload too large")
        root = ElementTree.fromstring(xml)
        def get(node, tag):
            return node.findtext("c:"+tag, default="", namespaces=self.namespace)
        common = {k: get(root, k) for k in ("identifier", "sender", "sent", "status", "msgType", "scope", "references")}
        if not common["identifier"] or common["status"] != "Actual" or common["scope"] != "Public":
            return []
        output = []
        for info in root.findall("c:info", self.namespace):
            item = {k: get(info, k) for k in ("event", "urgency", "severity", "certainty", "headline", "description", "instruction", "effective", "expires", "language")}
            polygons, circles, areas = [], [], []
            for area in info.findall("c:area", self.namespace):
                areas.append(get(area, "areaDesc"))
                for polygon in area.findall("c:polygon", self.namespace):
                    points = []
                    for point in (polygon.text or "").split():
                        lat, lon = map(float, point.split(","))
                        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                            raise ValueError("Invalid CAP polygon")
                        points.append([lon, lat])
                    if len(points) >= 4:
                        polygons.append(points)
                for circle in area.findall("c:circle", self.namespace):
                    coords, km = (circle.text or "").split()
                    lat, lon = map(float, coords.split(","))
                    if not -90 <= lat <= 90 or not -180 <= lon <= 180 or float(km) < 0:
                        raise ValueError("Invalid CAP circle")
                    circles.append([lat, lon, float(km)])
            output.append({**common, **item, "id": "cap:"+common["sender"]+":"+common["identifier"]+":"+item["language"],
                           "timestamp": common["sent"], "effective": item["effective"] or common["sent"],
                           "source": common["sender"], "data_source": "CAP · "+common["sender"],
                           "source_type": "official", "priority": 1, "original_severity": item["severity"],
                           "severity": {"Extreme": "SEVERE", "Severe": "WARNING", "Moderate": "WATCH"}.get(item["severity"], "INFO"),
                           "location": ", ".join(areas), "polygons": polygons, "circles": circles,
                           "alert_type": item["event"], "recommendation": item["instruction"], "model_source": "CAP bulletin"})
        return output
