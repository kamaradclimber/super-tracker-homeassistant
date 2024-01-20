import logging
import aiohttp
from typing import Optional, Tuple
from aiohttp.client import ClientTimeout
from math import cos

_LOGGER = logging.getLogger(__name__)

class OsmApi:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session or aiohttp.ClientSession()

    async def query_features(self, lat, lon, alt, radius):
        """
        This returns only the items that are *close* to the coordinates passed as arg
        """
        url = "https://overpass-api.de/api/interpreter"

        # TODO(kamaradclimber): improve computation for the area
        # currently using https://gis.stackexchange.com/a/2964
        min_lat = lat - radius / 111111.0
        max_lat = lat + radius / 111111.0
        min_lon = lon - radius / (111111.0 * cos(lat))
        max_lon = lon + radius / (111111.0 * cos(lat))

        data = f"[timeout:10][out:json];(node(around:33.75,{lat},{lon});way(around:{alt},{lat},{lon}););out tags geom({min_lat},{min_lon},{max_lat},{max_lon});relation(around:{alt},{lat},{lon});out geom({min_lat},{min_lon},{max_lat},{max_lon});"

        resp = await self._session.get(url, data={"data": data})
        if resp.status != 200:
            raise Exception(f"Could not query OSM, response had code {resp.status}")
        data = await resp.json()
        _LOGGER.debug(data)
        return data['elements']
