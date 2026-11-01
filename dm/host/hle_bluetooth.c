// nn::bluetooth / btm (Bluetooth LE, the Poké Ball Plus): the host has no Bluetooth adapter, so the whole API is made inert here
// instead of connecting to the "bt" service. That connection is what killed the game before the first frame: Pokémon: Let's Go,
// Pikachu! (SDK 5.4.151) calls InitializeBle from its Bluetooth manager constructor (main+0x1139d4) and then acquires the five
// events; InitializeBle starts the SDK's btm client, whose ConnectToHipcService("bt") is refused (the host does not serve it, and the
// service's replies would carry event handles the sf layer cannot hand out), and the SDK aborts inside the client.
// InitializeBle reports success, the five events are bound to kernel events that never fire, scans and connection lists are empty, and
// every GATT operation fails: the game runs as a console with no controller paired and takes its offline branch.
#include "hle.h"

HLE_FORCE("_ZN2nn9bluetooth13InitializeBleEv", "Bluetooth LE (Poké Ball Plus): no adapter, reports success so no btm client is started", Result, h_bt_Init, void) { return RES_OK; }

#define BT_QUIET_EVENT(mangled, cname)                                                                                                   \
    HLE_FORCE(mangled, "Bluetooth LE event: bound to a kernel event that never fires (no adapter)", void, cname, void *ev) { hle_bind_system_event(ev, 0); }

BT_QUIET_EVENT("_ZN2nn9bluetooth19AcquireBleScanEventEPNS_2os15SystemEventTypeE", h_bt_ScanEv)
BT_QUIET_EVENT("_ZN2nn9bluetooth37AcquireBleConnectionStateChangedEventEPNS_2os15SystemEventTypeE", h_bt_ConnEv)
BT_QUIET_EVENT("_ZN2nn9bluetooth31AcquireBleServiceDiscoveryEventEPNS_2os15SystemEventTypeE", h_bt_DiscEv)
BT_QUIET_EVENT("_ZN2nn9bluetooth24AcquireBleMtuConfigEventEPNS_2os15SystemEventTypeE", h_bt_MtuEv)
BT_QUIET_EVENT("_ZN2nn9bluetooth28AcquireBleGattOperationEventEPNS_2os15SystemEventTypeE", h_bt_GattEv)

// Scanning: starts and stops with success so the game's menu does not error, and no device is ever found
HLE_FORCE("_ZN2nn9bluetooth23StartBleScanSmartDeviceERKNS0_17GattAttributeUuidE", "BLE scan: no adapter, success and no results", Result, h_bt_ScanStart,
          const void *uuid) { (void)uuid; return RES_OK; }
HLE_FORCE("_ZN2nn9bluetooth22StopBleScanSmartDeviceEv", "BLE scan stop: no adapter, success", Result, h_bt_ScanStop, void) { return RES_OK; }
HLE_FORCE("_ZN2nn9bluetooth16GetBleScanResultEPNS0_13BleScanResultEi", "BLE scan results: none found", int, h_bt_ScanResults, void *out, int max) { (void)out; (void)max; return 0; }
HLE_FORCE("_ZN2nn9bluetooth24GetBleConnectionInfoListEPNS0_17BleConnectionInfoEi", "BLE connections: none", int, h_bt_ConnList, void *out, int max) { (void)out; (void)max; return 0; }
HLE_FORCE("_ZN2nn9bluetooth19GetBleScanParameterEPNS0_27BleAdvertisePacketParameterEi", "BLE scan filters: none registered", Result, h_bt_ParamAdv, void *out, int index) {
    (void)out; (void)index; return RES_FAIL;
}
HLE_FORCE("_ZN2nn9bluetooth19GetBleScanParameterEPNS0_17GattAttributeUuidEi", "BLE scan filters: none registered", Result, h_bt_ParamUuid, void *out, int index) {
    (void)out; (void)index; return RES_FAIL;
}

// GATT: there is no peer to connect to, so connecting and every operation fail
HLE_FORCE("_ZN2nn9bluetooth19ConnectToGattServerERKNS0_7AddressE", "GATT: no adapter, cannot connect", Result, h_bt_Connect, const void *addr) { (void)addr; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth24DisconnectFromGattServerEj", "GATT: no connection to close", Result, h_bt_Disconnect, uint32_t conn) { (void)conn; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth15ConfigureBleMtuEjt", "GATT: no connection, MTU not configured", Result, h_bt_Mtu, uint32_t conn, unsigned mtu) { (void)conn; (void)mtu; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth15GetGattServicesEPNS0_11GattServiceEij", "GATT: no service discovered", int, h_bt_Services, void *out, int max, uint32_t conn) {
    (void)out; (void)max; (void)conn; return 0;
}
HLE_FORCE("_ZN2nn9bluetooth22GetGattOperationResultEPNS0_26BleClientGattOperationInfoE", "GATT: no operation in flight", Result, h_bt_OpResult, void *out) { (void)out; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth22ReadGattCharacteristicERKNS0_18GattCharacteristicE", "GATT: no connection to read from", Result, h_bt_Read, const void *ch) { (void)ch; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth23WriteGattCharacteristicERKNS0_18GattCharacteristicE", "GATT: no connection to write to", Result, h_bt_Write, const void *ch) { (void)ch; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth19WriteGattDescriptorERKNS0_14GattDescriptorE", "GATT: no connection to write to", Result, h_bt_WriteDesc, const void *d) { (void)d; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth36EnableGattCharacteristicNotificationERKNS0_18GattCharacteristicEb", "GATT: no connection for notifications", Result, h_bt_Notify,
          const void *ch, int on) { (void)ch; (void)on; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth33RegisterGattOperationNotificationERKNS0_17GattAttributeUuidE", "GATT: no adapter to watch", Result, h_bt_RegOp, const void *uuid) { (void)uuid; return RES_FAIL; }
HLE_FORCE("_ZN2nn9bluetooth35UnregisterGattOperationNotificationERKNS0_17GattAttributeUuidE", "GATT: nothing registered", Result, h_bt_UnregOp, const void *uuid) { (void)uuid; return RES_FAIL; }
