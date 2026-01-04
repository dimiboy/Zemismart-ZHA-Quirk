import logging
import re
import random
import sys
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_registry import (
    async_get as async_entity_registry_get,
    EVENT_ENTITY_REGISTRY_UPDATED,
)
from zigpy.types import EUI64

DOMAIN = "zha_namehook"
VERSION = "9.0.0"  # Nuclear Option: Raw ZCL Injection

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    _LOGGER.info("Initializing %s (v%s). Strategy: Raw ZCL Injection.", DOMAIN, VERSION)
    async def _wrapped_handler(event):
        await async_entity_registry_update_handler(hass, event)
    hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, _wrapped_handler)
    return True

async def async_entity_registry_update_handler(hass, event):
    try:
        data = event.data
        if data.get('action') != 'update': return
        if 'changes' not in data or 'name' not in data['changes']: return

        entity_id = data.get('entity_id')
        old_name = data['changes'].get('name')
        
        entity_registry = async_entity_registry_get(hass)
        entry = entity_registry.async_get(entity_id)
        if not entry: return
        new_name = entry.name or ""
        if new_name == old_name: return

        device_id = entry.device_id
        if not device_id: return
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(device_id)
        if not device_entry: return

        ieee_str = next((idf for dom, idf in device_entry.identifiers if dom == 'zha'), None)
        if not ieee_str: return
        try: ieee_eui = EUI64.convert(ieee_str)
        except Exception: return

        zha_data = hass.data.get('zha')
        if not zha_data: return
        zha_device = zha_data.gateway_proxy.device_proxies.get(ieee_eui)
        if not zha_device: return

        # 1. Get Raw Endpoint
        # We need the low-level 'zigpy_endpoint' to send raw frames
        raw_ep = None
        endpoint = zha_device.device.endpoints.get(1)
        if endpoint:
             raw_ep = getattr(endpoint, 'zigpy_endpoint', endpoint)

        if not raw_ep:
            _LOGGER.error("[NameHook] Could not find raw endpoint.")
            return

        # 2. Prepare Data
        channel = get_channel_from_entity_id(entity_id)
        dp_id = 104 + channel 
        data_bytes = new_name.encode("utf-8")
        trans_id = random.randint(1, 255)
        
        _LOGGER.info("[NameHook] Renaming '%s' (DP %s)...", new_name, dp_id)

        # 3. Construct Tuya Data Payload
        # Format: [Status(1)] [TransID(1)] [DP(1)] [Type(1)] [Len(2)] [Data(N)]
        # This is the standard Tuya MCU protocol payload.
        tuya_payload = (
            b'\x00' +                      # Status: 0
            trans_id.to_bytes(1, "big") +  # Transaction ID
            dp_id.to_bytes(1, "big") +     # DP ID
            b'\x00' +                      # Type: 0 (Raw)
            len(data_bytes).to_bytes(2, "big") + # Length
            data_bytes                     # Actual Name
        )

        # 4. Construct ZCL Header
        # Frame Control: 0x01 (Cluster Command | Client->Server)
        # Sequence Number: Random
        # Command ID: 0x00 (SET_DATA)
        frame_control = b'\x01' 
        seq_num = random.randint(1, 255).to_bytes(1, "big")
        cmd_id = b'\x00'
        
        zcl_frame = frame_control + seq_num + cmd_id + tuya_payload

        # 5. Send Raw Request
        # We use 'request' on the endpoint to send the raw bytes to cluster 0xEF00
        # This bypasses all Python object checks.
        try:
            _LOGGER.info("[NameHook] Injecting Raw ZCL Frame: %s", zcl_frame.hex())
            await raw_ep.request(
                cluster=0xEF00,
                sequence=int.from_bytes(seq_num, "big"),
                data=zcl_frame,
                command_id=0x00,
                expect_reply=False
            )
            _LOGGER.info("[NameHook] Success! Packet injected.")
        except Exception as e:
            _LOGGER.error("[NameHook] Raw injection failed: %s", e)

    except Exception as ex:
        _LOGGER.error("[NameHook] Error: %s", ex, exc_info=True)

def get_channel_from_entity_id(entity_id: str) -> int:
    match = re.search(r'_(\d+)$', entity_id)
    if match:
        return ((int(match.group(1)) - 1) % 4) + 1
    return 1
