# tests/test_geolocate.py
# Unit tests for IP geolocation source.

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from news.sources.geolocate import (
    GeoResult,
    geolocate,
    geolocate_self,
    reverse_geocode,
    GeolocateSource,
)


SAMPLE_IPAPI_RESPONSE = {
    "status": "success",
    "country": "United States",
    "countryCode": "US",
    "region": "CA",
    "regionName": "California",
    "city": "Mountain View",
    "lat": 37.4056,
    "lon": -122.0775,
    "org": "AS15169 Google Inc.",
    "isp": "Google",
    "as": "AS15169 Google Inc.",
    "timezone": "America/Los_Angeles",
}


SAMPLE_IPINFO_RESPONSE = {
    "ip": "8.8.8.8",
    "city": "Mountain View",
    "region": "California",
    "country": "US",
    "loc": "37.4056,-122.0775",
    "org": "AS15169 Google Inc.",
    "timezone": "America/Los_Angeles",
}


class TestGeolocate(unittest.TestCase):
    @patch("news.sources.geolocate._fetch_apis", return_value=None)
    @patch("news.sources.geolocate._fetch_ipinfo", return_value=None)
    @patch("news.sources.geolocate._fetch_ipapi")
    def test_geolocate_uses_ipapi(self, mock_ipapi, mock_ipinfo, mock_apis):
        mock_ipapi.return_value = GeoResult(
            ip="8.8.8.8", lat=37.4056, lon=-122.0775,
            city="Mountain View", region="California",
            country="United States", country_code="US",
            isp="Google", org="AS15169 Google Inc.", asn="AS15169",
            timezone="America/Los_Angeles", source="ip-api.com",
        )
        result = geolocate("8.8.8.8")
        self.assertIsNotNone(result)
        self.assertEqual(result.country, "United States")
        self.assertEqual(result.lat, 37.4056)
        self.assertEqual(result.source, "ip-api.com")

    @patch("news.sources.geolocate._fetch_apis", return_value=None)
    @patch("news.sources.geolocate._fetch_ipapi", return_value=None)
    @patch("news.sources.geolocate._fetch_ipinfo")
    def test_geolocate_falls_back_to_ipinfo(self, mock_ipinfo, mock_ipapi, mock_apis):
        mock_ipinfo.return_value = GeoResult(
            ip="1.1.1.1", lat=0.0, lon=0.0,
            city=None, region=None,
            country="US", country_code=None,
            isp=None, org="Cloudflare", asn="Cloudflare",
            timezone=None, source="ipinfo.io",
        )
        result = geolocate("1.1.1.1")
        self.assertIsNotNone(result)
        self.assertEqual(result.source, "ipinfo.io")

    def test_geolocate_localhost(self):
        # localhost should be skipped
        self.assertIsNone(geolocate("127.0.0.1"))
        self.assertIsNone(geolocate("localhost"))
        self.assertIsNone(geolocate(""))

    @patch("news.sources.geolocate._fetch_apis")
    def test_geolocate_uses_apis_first(self, mock_apis):
        mock_apis.return_value = GeoResult(
            ip="8.8.8.8", lat=37.4, lon=-122.0,
            city="MV", region="CA", country="US", country_code="US",
            isp="Google", org="AS15169", asn="AS15169",
            timezone="PST", source="neohiro/apis",
        )
        with patch("news.sources.geolocate._APIS_BASE", "https://api.neohiro.io"):
            result = geolocate("8.8.8.8")
        self.assertEqual(result.source, "neohiro/apis")

    def test_reverse_geocode_handles_failure(self):
        # Should return None on network failure (no mock, will try real call)
        # We just ensure it doesn't raise
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("nope")):
            result = reverse_geocode(0, 0)
        self.assertIsNone(result)

    def test_geo_result_to_dict(self):
        r = GeoResult(
            ip="8.8.8.8", lat=37.4, lon=-122.0,
            city="MV", region="CA", country="US", country_code="US",
            isp="Google", org="AS15169", asn="AS15169",
            timezone="PST", source="test",
        )
        d = r.to_dict()
        self.assertEqual(d["ip"], "8.8.8.8")
        self.assertEqual(d["lat"], 37.4)
        self.assertEqual(d["country"], "US")


if __name__ == "__main__":
    unittest.main()
