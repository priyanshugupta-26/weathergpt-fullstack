# Data sources and attribution

- **Open-Meteo:** forecast, historical archive, air-quality and marine HTTP APIs. Numerical model outputs, not local station readings. See https://open-meteo.com/en/docs and the provider's usage terms for public/commercial operation.
- **USGS:** M2.5+ earthquake GeoJSON feed covering the last 24 hours. Reports may be revised by USGS. https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
- **Natural Earth:** 1:110m country boundaries, public domain. Local copy of `ne_110m_admin_0_countries.geojson` from https://github.com/nvkelso/natural-earth-vector. https://www.naturalearthdata.com/about/terms-of-use/
- **GeoNames:** local city gazetteer derived from `cities5000.zip`, downloaded 2026-09-09 from https://download.geonames.org/export/dump/cities5000.zip. Licensed under Creative Commons Attribution 4.0: https://creativecommons.org/licenses/by/4.0/. https://www.geonames.org/ supplies the underlying geographic names and coordinates. The conversion keeps name, ASCII name, aliases, coordinates, country, population (for result ranking), and timezone; it sorts by population. This static geographic data is not weather data. City matches are available offline; district/smaller-place queries fall through to the online geocoder when absent from the local gazetteer.

No generated or demo weather values are shown as live. Test fixture weather is confined to tests.
