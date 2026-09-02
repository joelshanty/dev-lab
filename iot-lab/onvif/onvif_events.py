"""
ONVIF event listener for IP cameras and ONVIF-compatible devices.

This script connects to a device over the ONVIF SOAP API, retrieves the
Events service endpoint from the device capabilities, subscribes to a
PullPoint subscription, and continuously polls for event notifications.

Requirements:
    - A reachable ONVIF camera/nvr/device on the network
    - Valid ONVIF credentials (username/password)
    - Python packages: requests, zeep

Configuration:
    Update the IP, PORT, USERNAME, and PASSWORD values below before running.

Usage:
    python onvif_events.py

Notes:
    Some devices only support a subset of ONVIF event features, and the event
    service may require PullPoint or PullMessages support.
"""

import asyncio
from functools import partial
import os
import tempfile
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from zeep import Client, Transport, Settings
from zeep.cache import SqliteCache
import json


# ---------------------------------------------------------------------------
# Device configuration
# Update these values before running the script.
# ---------------------------------------------------------------------------
IP = "<Give the IP of the device>"
PORT = 80
USERNAME = "<Give the Username>"
PASSWORD = "<Give the Password>"


# ONVIF WSDL files used to build SOAP client services.
EVENTS_WSDL = "https://www.onvif.org/ver10/events/wsdl/event.wsdl"
DEVICE_WSDL = "https://www.onvif.org/ver10/device/wsdl/devicemgmt.wsdl"


class ONVIFDevice:
    def __init__(self, ip, username, password, port=80, use_ssl=False):
        # Store the device connection details and build the ONVIF device service URL.
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.url = f"http{'s' if use_ssl else ''}://{ip}:{port}/onvif/device_service"
        self.client = None
        self.events_url = None

    # ---------------------------------------------------------------------
    # Transport setup
    # ---------------------------------------------------------------------
    def _create_transport(self):
        cache_dir = os.path.join(tempfile.gettempdir(), "onvif_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache = SqliteCache(path=os.path.join(cache_dir, "onvif.db"), timeout=3600)
        transport = Transport(cache=cache, timeout=30)

        transport.session.auth = HTTPDigestAuth(self.username, self.password)
        transport.session.headers.update({"User-Agent": "python-onvif-client/1.0"})

        retry_strategy = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        transport.session.mount("http://", adapter)
        transport.session.mount("https://", adapter)
        return transport

    # ---------------------------------------------------------------------
    # SOAP client creation
    # ---------------------------------------------------------------------
    def _create_client(self, wsdl_url):
        try:
            # Build a reusable SOAP client for the specified ONVIF WSDL definition.
            transport = self._create_transport()
            settings = Settings(strict=False, xml_huge_tree=True, forbid_dtd=False)
            client = Client(wsdl=wsdl_url, transport=transport, settings=settings)
            return client
        except Exception as e:
            print(f"❌ Failed to create SOAP client: {e}")
            return None

    # ---------------------------------------------------------------------
    # Capability discovery
    # ---------------------------------------------------------------------
    def _get_capabilities(self):
        """Fetch device capabilities to find service URLs."""
        try:
            client = self._create_client(DEVICE_WSDL)
            if not client:
                return None
            service = client.create_service(
                "{http://www.onvif.org/ver10/device/wsdl}DeviceBinding", self.url
            )
            capabilities = service.GetCapabilities("Events")

            return capabilities
        except Exception as e:
            print(f"❌ Failed to get capabilities: {e}")
            return None

    # ---------------------------------------------------------------------
    # Event subscription
    # ---------------------------------------------------------------------
    async def subscribe_events(self):
        subscription_service = None
        try:
            # Discover the event service endpoint from the device's capabilities.
            capabilities = self._get_capabilities()
            if not capabilities or not capabilities.Events:
                print("❌ Events service not available on this device.")
                return None

            self.events_url = capabilities.Events.XAddr

            # Create a client for the event WSDL and request a PullPoint subscription.
            events_client = self._create_client(EVENTS_WSDL)
            service = events_client.create_service(
                "{http://www.onvif.org/ver10/events/wsdl}EventBinding",
                self.events_url,
            )
            loop = asyncio.get_event_loop()
            subscribe_func = partial(service.CreatePullPointSubscription)
            subscription = await loop.run_in_executor(None, subscribe_func)

            # Use the returned subscription address to bind to the pull-point service.
            sub_address = subscription.SubscriptionReference.Address._value_1

            subscription_client = self._create_client(EVENTS_WSDL)
            if not subscription_client:
                return

            subscription_service = subscription_client.create_service(
                "{http://www.onvif.org/ver10/events/wsdl}PullPointSubscriptionBinding",
                sub_address,
            )

        except Exception as e:
            print(f"❌ Failed to subscribe to events from {self.ip}: {e}")
            return None
        return subscription_service

    # ---------------------------------------------------------------------
    # Event polling
    # ---------------------------------------------------------------------
    async def pull_events(self, subscription_service, timeout=10, message_limit=10):
        loop = asyncio.get_event_loop()
        result = []
        event_time = None
        try:
            pull_func = partial(
                subscription_service.PullMessages,
                Timeout=f"PT{timeout}S",
                MessageLimit=message_limit,
            )
            response = await loop.run_in_executor(None, pull_func)
            # print(response)

            if hasattr(response, "CurrentTime"):
                event_time = int(response.CurrentTime.timestamp() * 1000)

            if hasattr(response, "NotificationMessage"):
                messages = response.NotificationMessage
                for i, message in enumerate(messages):
                    parsed_msg = self.extract_message_data(message)
                    if event_time:
                        parsed_msg["event_time"] = event_time
                    result.append(parsed_msg)
        except Exception as e:
            result = {"error": str(e)}
        return result

    # ---------------------------------------------------------------------
    # Message parsing
    # ---------------------------------------------------------------------
    def extract_message_data(self, message):
        """Extract complete message data from ONVIF event."""
        msg_data = {}
        try:
            if not hasattr(message, "Message"):
                raise Exception("No Message attribute found")
            msg = message.Message
            xml_element = getattr(msg, "_value_1", msg)
            # print(f"======={raw_xml}")
            if xml_element is None:
                raise Exception("No XML element found")
            NS = {"tt": "http://www.onvif.org/ver10/schema"}
            result = {}
            utc_time = xml_element.get("UtcTime")
            if utc_time:
                result["utcTime"] = utc_time

            # Extract all Source items
            source_items = xml_element.findall(".//tt:Source/tt:SimpleItem", NS)
            for item in source_items:
                name = item.get("Name")
                value = item.get("Value")
                if name and value:
                    result[name] = value

            # Extract all Key items
            key_items = xml_element.findall(".//tt:Key/tt:SimpleItem", NS)
            for item in key_items:
                name = item.get("Name")
                value = item.get("Value")
                if name and value:
                    result[name] = value

            # Extract all Data items
            data_items = xml_element.findall(".//tt:Data/tt:SimpleItem", NS)
            for item in data_items:
                name = item.get("Name")
                value = item.get("Value")
                if name and value:
                    result[name] = value
            # Extract any other top-level attributes
            for attr_name, attr_value in xml_element.attrib.items():
                if attr_name not in ["UtcTime"]:
                    result[f"message_{attr_name.lower()}"] = attr_value
            # Look for any other elements not in Source/Key/Data
            other_elements = {}
            for child in xml_element:
                child_tag = child.tag.replace("{http://www.onvif.org/ver10/schema}", "")
                if child_tag not in ["Source", "Key", "Data"]:
                    if child.text:
                        other_elements[child_tag] = child.text
                    # Handle nested elements
                    for subchild in child:
                        subchild_tag = subchild.tag.replace(
                            "{http://www.onvif.org/ver10/schema}", ""
                        )
                        if subchild.text:
                            other_elements[f"{child_tag}_{subchild_tag}"] = (
                                subchild.text
                            )
            if other_elements:
                result["other"] = other_elements
            print(f"----------------------{msg_data}")
        except Exception as e:
            msg_data = {"error": f"Message data extraction error: {e}"}
        return msg_data

    # ---------------------------------------------------------------------
    # Main event loop
    # ---------------------------------------------------------------------
    async def run_event_listener(self):
        print("Attempting to subscribe to events...")
        subscription_service = await self.subscribe_events()
        if not subscription_service:
            print("Could not create event subscription. Exiting.")
            return

        print("✅ Successfully subscribed to events. Now pulling messages...")
        while True:
            try:
                # Poll the ONVIF subscription for new notifications.
                event_responses = await self.pull_events(
                    subscription_service, timeout=30, message_limit=10
                )
                if event_responses:
                    print(f"\n--- Received Events ---")
                    print(json.dumps(event_responses, indent=2))
                else:
                    print(".", end="", flush=True)
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping event listener.")
                break
            except Exception as e:
                print(f"\nAn error occurred while pulling events: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":

    # Clear Zeep cache to ensure fresh WSDL downloads when starting a new session.
    cache_dir = os.path.join(tempfile.gettempdir(), "onvif_cache")
    if os.path.exists(cache_dir):
        print(f"Clearing Zeep cache at: {cache_dir}")
        import shutil
        shutil.rmtree(cache_dir)

    device = ONVIFDevice(IP, USERNAME, PASSWORD, PORT)
    try:
        asyncio.run(device.run_event_listener())
    except KeyboardInterrupt:
        print("\nSimulator finished.")
