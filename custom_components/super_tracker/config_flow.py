from copy import deepcopy
import logging
from typing import Any, Dict, Optional

from homeassistant.helpers.selector import DeviceSelector, DeviceSelectorConfig, DeviceFilterSelectorConfig
from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
)
import voluptuous as vol

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE_ID = "device_id"

device_selector_config = DeviceSelectorConfig(
        multiple=False,
        filter=DeviceFilterSelectorConfig(
            integration="mobile_app"
        )
)

INPUT_DEVICE_SCHEMA= vol.Schema(
        {vol.Required(CONF_DEVICE_ID): DeviceSelector(device_selector_config)}
)

class SetupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            self.data = user_input
            return self.async_create_entry(title=f"Super Tracker for {self.data[CONF_DEVICE_ID]}", data=self.data)
        return self.async_show_form(
            step_id="user", data_schema=INPUT_DEVICE_SCHEMA, errors=errors
        )
