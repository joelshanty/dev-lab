"""
ONVIF utility script for interacting with ONVIF-compatible NVRs/ IP cameras and devices.

Overview:
    This script connects to a device using the ONVIF Device Management and Media
    services, retrieves basic device information, checks capabilities, inspects
    media profiles/stream URIs, and can subscribe to event notifications.

Prerequisites:
    - Python environment with the `zeep` and `requests` packages installed.
    - A reachable ONVIF device on the local network.
    - Valid username and password for the device.

Configuration:
    Update the values below before running the script:
        IP       -> camera/device IP address
        PORT     -> ONVIF port (often 80 or 5000)
        USERNAME -> device username
        PASSWORD -> device password

Usage:
    1. Fill in the credentials in this file.
    2. Run: python onvif_utils.py
    3. The script will initialize the connection and print discovered device info.

Notes:
    - Some device features depend on ONVIF support and the advertised capabilities.
    - Event subscriptions may require a camera to support PullPoint or PullMessages.
    - Network access, firewall settings, and certificate/HTTPS configuration may
      affect the connection depending on the device.
"""

import time
from zeep import helpers
from zeep import Client
from zeep.transports import Transport
from requests.auth import HTTPDigestAuth
from zeep.helpers import serialize_object

# Device credentials
IP = "<Give the IP of the device>"
PORT = "<Give the Port of the device>"
USERNAME = "<Give the Username>"
PASSWORD = "<Give the Password>"


# Create the WSDL URL for the device management service
WSDL_URL = "https://www.onvif.org/ver10/device/wsdl/devicemgmt.wsdl"
MEDIA_WSDL = "https://www.onvif.org/ver10/media/wsdl/media.wsdl"
EVENT_WSDL = "https://www.onvif.org/ver10/events/wsdl/event.wsdl"


class ONVIFDevice:
    def __init__(self):
        self.transport = None
        self.device_service = None
        self.media_service = None
        self.event_service = None

    # ----------- 1 ----------- Initializing connection -----------
    def _init_connection(self):
        try:
            device_service_url = f"http://{IP}:{PORT}/onvif/device_service"
            self.transport = Transport()
            self.transport.session.auth = HTTPDigestAuth(USERNAME, PASSWORD)
            self.transport.session.timeout = 30
            device_client = Client(wsdl=WSDL_URL, transport=self.transport)
            self.device_service = device_client.create_service(
                "{http://www.onvif.org/ver10/device/wsdl}DeviceBinding",
                device_service_url,
            )
            media_client = Client(wsdl=MEDIA_WSDL, transport=self.transport)
            self.media_service = media_client.create_service(
                "{http://www.onvif.org/ver10/media/wsdl}MediaBinding",
                f"http://{IP}:{PORT}/onvif/media_service",
            )
            
        except Exception as e:
            print(f"Error initializing connection: {e}")

    # ----------- 2 ----------- Get device informations -----------
    def get_device_information(self):
        dev_info = {}
        try:
            info = self.device_service.GetDeviceInformation()
            info_dict = serialize_object(info)
            for key, value in info_dict.items():
                dev_info[key] = value
        except Exception as e:
            print(f"Error getting device information: {e}")
        return dev_info

    # ----------- 3 ----------- Get device capabilities -----------
    def get_device_capabilities(self):
        dev_capabilities = {}
        try:
            capabilities = self.device_service.GetCapabilities()
            capabilities_dict = helpers.serialize_object(capabilities)

            dev_cap = [
                key
                for key in capabilities_dict.keys()
                if key not in ["Extension", "_attr_1", "_value_1"]
            ]
            dev_capabilities["Capabilities"] = dev_cap
            # for cap in dev_cap:
            #     cap_conf = capabilities_dict.get(cap)
            #     dev_capabilities[f"{cap}_conf"] = {"XAddr": cap_conf.get("XAddr")}
                
            scopes = self.device_service.GetScopes()
            print(f"Scopes: {scopes}")

        except Exception as e:
            print(f"Error getting device information: {e}")
        return dev_capabilities
    
    # ----------- 4 ----------- Get device storage configurations -----------
    def get_device_storage_configurations(self):
        try:
            from onvif import ONVIFCamera

            nvr = ONVIFCamera(IP, PORT, USERNAME, PASSWORD)

            devicemgmt = nvr.create_devicemgmt_service()

            # Try system date/time + general device info first (sanity check)
            print(devicemgmt.GetDeviceInformation())
        except Exception as e:
            print(f"Error getting storage information: {e}")

    # ----------- 4 ----------- Get device storage configurations -----------
    def get_device_storage_configurations(self):
        """only availabler if Storage Service capability exists while calling get_device_capabilities"""
        storage_conf = {}
        try:
            storage_conf = self.device_service.GetStorageConfigurations()
        except Exception as e:
            print(f"Error getting storage information: {e}")
        return storage_conf

    # ----------- 6 ----------- Get Network Protocols -----------
    def get_device_data(self):
        """All other operations that can be performed on the device"""
        data = {}
        try:
            # data = self.device_service.GetNetworkProtocols()
            # data = self.device_service.GetDiscoveryMode()
            data = self.device_service.GetSystemDateAndTime()
        except Exception as e:
            print(f"Error getting storage information: {e}")
        return data

    # ----------- 7 ----------- Get Media stream info -----------
    def get_stream_info(self):
        data = {}
        try:
            profiles = self.media_service.GetProfiles()
            # print(profiles)
            for profile in profiles:
                print(
                    "-----------------------------------------------------------------"
                )
                print(f"Profile Name: {profile.Name}")
                print(f"Profile Token: {profile.token}")
                # print(f"Source token: {profile.VideoSourceConfiguration.SourceToken}")
                print(f"Profile : {profile}")

                # Use the service directly with keyword arguments
                uri_response = self.media_service.GetStreamUri(
                    StreamSetup={
                        "Stream": "RTP-Unicast",
                        "Transport": {"Protocol": "RTSP"},
                    },
                    ProfileToken=profile.token,
                )

                print(uri_response)
                # break

        except Exception as e:
            print(f"Error getting media profile information: {e} : {profile}")
        return data

    def subscribe_and_poll_events(self):
        caps = self.device_service.GetCapabilities()
        event_xaddr = getattr(caps, 'Events', None)
        event_service_url = None        
        if event_xaddr and hasattr(event_xaddr, 'XAddr'):
            event_service_url = event_xaddr.XAddr
            print(f"Event url: {event_service_url}")
        if not event_service_url:
            raise Exception(f"Event url failed to retrieve")
        
        event_client = Client(wsdl=EVENT_WSDL, transport=self.transport)
        self.event_service = event_client.create_service(
                "{http://www.onvif.org/ver10/events/wsdl}PullPointSubscriptionBinding",
                f"{event_service_url}",
            )
        
        service_ops = list(self.event_service._operations.keys())
        if 'CreatePullPointSubscription' in service_ops:
            print(f"[{IP}] PullPoint supported. Creating subscription...")
            pullpoint_element = event_client.get_element(
                '{http://www.onvif.org/ver10/events/wsdl}CreatePullPointSubscription'
            )
            request = pullpoint_element()
            request.InitialTerminationTime = "PT1H"

            pullpoint_response = self.event_service.CreatePullPointSubscription(request)
            pullpoint_xaddr = pullpoint_response.SubscriptionReference.Address
            print(f"[{IP}] PullPoint address: {pullpoint_xaddr}")

            # Create PullPoint service binding
            pullpoint_service = event_client.create_service(
                "{http://www.onvif.org/ver10/events/wsdl}PullPointSubscriptionBinding",
                pullpoint_xaddr
            )
            self.event_service = pullpoint_service

        # Step 5: Fallback for cameras with PullMessages only
        elif 'PullMessages' in service_ops:
            print(f"[{IP}] PullMessages only supported. Will pull directly.")
            self.event_service = self.event_service

        else:
            raise Exception(f"[{IP}] No supported event operations found!")

        # Step 6: Poll events
        while True:
            try:
                if 'PullMessages' in service_ops:
                    messages = self.event_service.PullMessages(Timeout="PT10S", MessageLimit=10)

                    print(messages)
                    for msg in getattr(messages, 'NotificationMessage', []):
                        print(f"[{IP}] Event: {msg}")

                # If using PullPoint, you can also call PullMessages here similarly
                time.sleep(5)  # Poll every 5 seconds

            except Exception as e:
                print(f"[{IP}] Error polling events: {e}")
                time.sleep(5)


    def main(self):
        print("----------- 1 ----------- Initializing connection -----------")
        self._init_connection()

        print("----------- 2 ----------- Get device informations -----------")
        device_info = self.get_device_information()
        if not device_info:
            print("Failed to get device information...")
            return
        print(device_info)

        print("----------- 3 ----------- Get device capabilities -----------")
        device_capabilities = self.get_device_capabilities()
        if not device_capabilities:
            print("Failed to get device capabilities...")
            return
        print(device_capabilities)

        print("----------- 4 ----------- Get device storage configurations -----------")
        storage_info = self.get_device_storage_configurations()
        if not storage_info:
            print("Failed to get device storage information...")
        print(storage_info)

        print("----------- 5 ----------- Get Network Protocols -----------")
        network_protocols = self.get_device_data()
        if not network_protocols:
            print("Failed to get information...")
            return
        print(network_protocols)

        print("----------- 7 ----------- Get Media stream info -----------")
        self.get_stream_info()

        print("----------- 8 ----------- Subscribing and Polling events -----------")
        self.subscribe_and_poll_events()


if __name__ == "__main__":

    print(" ----------- ONVIF DISCOVERY ----------- ")
    onvif_device = ONVIFDevice()
    onvif_device.main()