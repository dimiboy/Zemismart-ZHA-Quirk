"""Zemismart 4 Gang Switch Quirk _TZE284_y4jqpry8 - Exact Match & Simple String."""
import logging
from zigpy.profiles import zha, zgp
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Scenes,
    Time,
    Ota,
    GreenPowerProxy,
)
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaSwitch, TuyaData
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaOnOffManufCluster,
    TuyaOnOff,
)
import zigpy.types as t

_LOGGER = logging.getLogger(__name__)

# --- Data Types ---
class RawBytes(TuyaData):
    """Raw bytes data type for string encoding (Simple Format)."""
    def __init__(self, value: bytes):
        self.value = value
    
    def serialize(self) -> bytes:
        # device expects raw string bytes, no length header
        return self.value
        
    def __repr__(self):
        return f"<RawBytes {self.value!r}>"

# --- Custom Cluster ---
class CustomTuyaManufCluster(TuyaOnOffManufCluster):
    """Custom Tuya cluster with Naming Support."""
    
    # Register attributes to prevent write errors
    attributes = TuyaOnOffManufCluster.attributes.copy()
    attributes.update({
        0xEF01: ("name_update_1", t.CharacterString),
        0xEF02: ("name_update_2", t.CharacterString),
        0xEF03: ("name_update_3", t.CharacterString),
        0xEF04: ("name_update_4", t.CharacterString),
    })

    dp_to_attribute = TuyaOnOffManufCluster.dp_to_attribute.copy()
    dp_to_attribute.update({
        # Switch State Mappings (Standard Tuya DPs)
        1: DPToAttributeMapping(TuyaOnOff.ep_attribute, "on_off", endpoint_id=1),
        2: DPToAttributeMapping(TuyaOnOff.ep_attribute, "on_off", endpoint_id=2),
        3: DPToAttributeMapping(TuyaOnOff.ep_attribute, "on_off", endpoint_id=3),
        4: DPToAttributeMapping(TuyaOnOff.ep_attribute, "on_off", endpoint_id=4),
        # Name Update Mappings (Zemismart proprietary - Simple Format)
        105: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_1",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        106: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_2",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        107: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_3",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
        108: DPToAttributeMapping(
            ep_attribute="tuya_mcu",
            attribute_name="name_update_4",
            converter=lambda x: x.decode("utf-8"),
            dp_converter=lambda x: RawBytes(x.encode("utf-8")),
            endpoint_id=1,
        ),
    })

class TuyaQuadrupleSwitch(TuyaSwitch):
    """_TZE284_y4jqpry8 TS0601 4-gang switch."""

    def __init__(self, *args, **kwargs):
        self._endpoint_id = {1: 1, 2: 2, 3: 3, 4: 4}
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [
            ("_TZE284_y4jqpry8", "TS0601"),
        ],
        ENDPOINTS: {
            # 1. Main Endpoint (Matches your device logs exactly)
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    0xED00, # Tuya Manufacturer Specific
                    0xEF00, # Tuya MCU
                ], 
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # 2. Green Power Endpoint (Matches your device logs)
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    CustomTuyaManufCluster, # Loads our custom logic
                    TuyaOnOff,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOff],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOff],
                OUTPUT_CLUSTERS: [],
            },
            4: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [TuyaOnOff],
                OUTPUT_CLUSTERS: [],
            },
            # Keep Green Power endpoint pass-through
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
