from __future__ import annotations

import logging

from propcache.api import cached_property

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SwissWeatherDataCoordinator, get_weather_coordinator_key
from .const import CONF_POST_CODE, CONF_STATION_CODE, DOMAIN
from .meteo import Warning, WarningLevel, WarningType
from .sensor import get_color_for_warning_level, get_warning_of_type

_LOGGER = logging.getLogger(__name__)

# Swiss heat wave warnings are only issued from level 2 (moderate hazard) upwards.
HEAT_WAVE_MIN_LEVEL = WarningLevel.MODERATE_HAZARD

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SwissWeatherDataCoordinator = hass.data[DOMAIN][get_weather_coordinator_key(config_entry)]
    postCode: str = config_entry.data[CONF_POST_CODE]
    stationCode: str = config_entry.data.get(CONF_STATION_CODE)

    if stationCode is None:
        id_combo = f"{postCode}"
    else:
        id_combo = f"{postCode}-{stationCode}"
    deviceInfo = DeviceInfo(entry_type=DeviceEntryType.SERVICE, name=f"MeteoSwiss at {id_combo}", identifiers={(DOMAIN, f"swissweather-{id_combo}")})

    async_add_entities([SwissWeatherHeatWaveSensor(postCode, deviceInfo, coordinator)])


class SwissWeatherHeatWaveSensor(CoordinatorEntity[SwissWeatherDataCoordinator], BinarySensorEntity):
    """Indicates whether a heat wave warning (level 2 or higher) is currently active."""

    def __init__(self, post_code: str, device_info: DeviceInfo, coordinator: SwissWeatherDataCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_name = f"Heat wave at {post_code}"
        self._attr_unique_id = f"{post_code}.heat_wave"
        self._attr_device_info = device_info
        self._attr_attribution = "Source: MeteoSwiss"
        self._entity_component_unrecorded_attributes = MATCH_ALL

    def _get_warning(self) -> Warning | None:
        return get_warning_of_type(self.coordinator.data, WarningType.HEAT_WAVES)

    @property
    def is_on(self) -> bool:
        warning = self._get_warning()
        if warning is None:
            return False
        return warning.warningLevel >= HEAT_WAVE_MIN_LEVEL

    @property
    def extra_state_attributes(self) -> dict[str, any] | None:
        """Return additional state attributes."""
        warning = self._get_warning()
        if warning is None:
            return {
                'level': "No danger",
                'level_numeric': WarningLevel.NO_DANGER,
                'icon_color': get_color_for_warning_level(WarningLevel.NO_DANGER)
            }
        return {
            'level': warning.warningLevel.name.replace('_', ' ').capitalize(),
            'level_numeric': warning.warningLevel,
            'text': warning.text,
            'html_text': warning.htmlText,
            'valid_from': warning.validFrom,
            'valid_to': warning.validTo,
            'links': warning.links,
            'outlook': warning.outlook,
            'icon_color': get_color_for_warning_level(warning.warningLevel)
        }

    @cached_property
    def icon(self):
        return "mdi:sun-thermometer"
