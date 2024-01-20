import logging
import re
from typing import Any, Callable, Dict, Optional

from homeassistant.core import callback
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from homeassistant.helpers.event import async_track_state_change
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.helpers.device_registry import (
        DeviceEntry,
        DeviceRegistry,
        async_get
)
from homeassistant.helpers.entity_registry import (
        RegistryEntry,
        async_get as async_get_entity_registry,
        async_entries_for_device,
)
from .config_flow import CONF_DEVICE_ID
from .osm import OsmApi

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistantType,
        config: ConfigType,
        async_add_entities: Callable,
        discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    device_registry = async_get(hass)
    tracked_device = device_registry.async_get(config.data[CONF_DEVICE_ID])
    if tracked_device is None:
        raise Exception(f"Could not find device corresponding to {config.data[CONF_DEVICE_ID]}")
    entity_registry = async_get_entity_registry(hass)
    entities = async_entries_for_device(entity_registry, config.data[CONF_DEVICE_ID])
    device_tracker_entity = None
    upstream_activity_entity = None
    for e in entities:
        if re.match("device_tracker.", e.entity_id):
            device_tracker_entity = e
        if re.search(".*detected_activity", e.entity_id):
            upstream_activity_entity = e
    if device_tracker_entity is None:
        raise Exception(f"Could not find any device_tracker for device {tracked_device.name}")
    activity_desc = SensorEntityDescription(
      name="Enriched activity",
      key="enriched_activity"
    )
    activity = SuperTrackerActivity(activity_desc, tracked_device, hass, device_tracker_entity, upstream_activity_entity)
    async_add_entities([activity])

class SuperTrackerActivity(SensorEntity):
    def __init__(self, description, tracked_device: DeviceEntry, hass: HomeAssistantType, device_tracker_entity: RegistryEntry, upstream_activity_entity: RegistryEntry):
        super().__init__()
        self.entity_description = description
        self.tracked_device = tracked_device
        self._attr_native_value = 0
        self._attr_unique_id = f"#{self.tracked_device.id}_sensor_activity"
        self.hass_bus = hass.bus
        self.device_tracker = device_tracker_entity
        self.upstream_activity_entity = upstream_activity_entity

        self.osm_api = OsmApi()

    @callback
    async def receive_new_location(self, new_state):
        _LOGGER.warning(f"Receiving {new_state}")
        self.latitude = new_state.attributes['latitude']
        self.longitude = new_state.attributes['longitude']
        self.altitude = new_state.attributes['altitude']
        self.precision = new_state.attributes['gps_accuracy']
        features = await self.osm_api.query_features(self.latitude, self.longitude, self.altitude, self.precision)
        train_hints = 0
        for f in features:
            if "tags" in f:
                if "train" in f["tags"] or "railway" in f["tags"]:
                    train_hints += 1
        _LOGGER.warn(f"Found {train_hints} hints that we are close to train amenities")
        self._attr_native_value = train_hints


    @callback
    def receive_new_activity(self, new_state):
        _LOGGER.warning(f"Receiving {new_state}")
        self.upstream_activity_state = new_state.state

    async def async_added_to_hass(self):
        @callback
        async def handle_location_update(event):
            if event.data['entity_id'] == self.device_tracker.entity_id:
                await self.receive_new_location(event.data['new_state'])
            elif event.data['entity_id'] == self.upstream_activity_entity.entity_id:
                self.receive_new_activity(event.data['new_state'])
        self.hass_bus.async_listen(EVENT_STATE_CHANGED, handle_location_update)

