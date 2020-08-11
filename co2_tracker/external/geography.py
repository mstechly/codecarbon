"""
Encapsulates external dependencies to retrieve cloud, gpu and geographical metadata
"""

from co2_tracker_utils.cloud_logging import get_env_cloud_details
from co2_tracker_utils.gpu_logging import get_gpu_details, is_gpu_details_available
from dataclasses import dataclass
import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict, Callable

import requests
from co2_tracker_utils.cloud_logging import get_env_cloud_details

logger = logging.getLogger(__name__)


@dataclass
class CloudMetadata:

    provider: Optional[str]
    region: Optional[str]

    @property
    def is_on_private_infra(self) -> bool:
        return self.provider is None and self.region is None

    @classmethod
    def from_co2_tracker_utils(cls) -> "CloudMetadata":
        def extract_gcp_region(zone: str) -> str:
            """
            projects/705208488469/zones/us-central1-a -> us-central1
            """
            google_region_regex = r"[a-z]+-[a-z]+[0-9]"
            return re.search(google_region_regex, zone).group(0)

        extract_region_for_provider: Dict[str, Callable] = {
            "aws": lambda x: x["metadata"]["region"],
            "azure": lambda x: x["metadata"]["compute"]["location"],
            "gcp": lambda x: extract_gcp_region(x["metadata"]["zone"]),
        }

        cloud_metadata: Dict = get_env_cloud_details()

        if cloud_metadata is None:
            return cls(provider=None, region=None)

        provider: str = cloud_metadata["provider"].lower()
        region: str = extract_region_for_provider.get(provider)(cloud_metadata)

        return cls(provider=provider, region=region)


@dataclass
class GeoMetadata:

    country: str
    region: Optional[str] = None

    @classmethod
    def from_geo_js(cls, url: str) -> "GeoMetadata":
        try:
            response: Dict = requests.get(url, timeout=0.5).json()
        except requests.exceptions.Timeout:
            # If there is a timeout, we default to Canada
            logger.info(
                "Unable to access geographical location. Using 'Canada' as the default value"
            )
            return cls(country="Canada")
        return cls(country=response["country"], region=response["region"])