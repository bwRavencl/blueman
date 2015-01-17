import dbus
from blueman.Sdp import uuid128_to_uuid16, uuid16_to_name, sdp_get_cached_rfcomm
from blueman.bluez.BlueZInterface import BlueZInterface
from blueman.Lib import rfcomm_list


class Service(object):
    __group__ = None
    __svclass_id__ = None
    __description__ = None
    __icon__ = None
    __priority__ = None
    __interface__ = None

    _service = None
    _legacy_interface = None

    def __init__(self, device, uuid):
        self.__device = device
        self.__uuid = uuid
        if self.__interface__:
            self._service = self.__interface__(device.get_object_path())
        elif BlueZInterface.get_interface_version()[0] < 5:
            bus = dbus.SystemBus()
            proxy = bus.get_object("org.bluez", self.__device.get_object_path())
            self._legacy_interface = dbus.Interface(proxy, 'org.bluez.%s' % self.__class__.__name__)

    @property
    def name(self):
        return uuid16_to_name(uuid128_to_uuid16(self.__uuid))

    @property
    def device(self):
        return self.__device

    @property
    def uuid(self):
        return self.__uuid

    @property
    def description(self):
        return self.__description__

    @property
    def icon(self):
        return self.__icon__

    @property
    def priority(self):
        return self.__priority__

    @property
    def group(self):
        return self.__group__

    @property
    def ports(self):
        if self.group == 'serial':
            try:
                for port_name, channel, uuid in sdp_get_cached_rfcomm(self.device.Address):
                    if self.__svclass_id__ in uuid:
                        yield port_name, channel
            except KeyError:
                pass

    def serial_port_id(self, channel):
        for dev in rfcomm_list():
            if dev["dst"] == self.device.Address and dev["state"] == "connected" and dev["channel"] == channel:
                return dev["id"]

    @property
    def connected(self, *args):
        if self.group == 'serial':
            return self.serial_port_id(args[0])
        elif self._service:
            return self._service.get_properties()['Connected']
        elif self._legacy_interface:
            return self._legacy_interface.GetProperties()['Connected']
        else:
            return self.__device.Device.get_properties()['Connected']

    def connect(self, reply_handler=None, error_handler=None):
        if self._service:
            self._service.connect(self.uuid, reply_handler=reply_handler, error_handler=error_handler)
        elif self._legacy_interface:
            self._legacy_interface.Connect(self.__uuid, reply_handler=reply_handler, error_handler=error_handler)
        else:
            self.__device.Device.connect(reply_handler=reply_handler, error_handler=error_handler)

    def disconnect(self, reply_handler=None, error_handler=None, *args):
        if self._service:
            # TODO: TypeError: disconnect() got multiple values for keyword argument 'reply_handler'
            self._service.disconnect(self.uuid, reply_handler=reply_handler, error_handler=error_handler)
        elif self._legacy_interface:
            self._legacy_interface.Disconnect(self.__uuid, reply_handler=reply_handler, error_handler=error_handler)
        else:
            self.__device.Device.disconnect(reply_handler=reply_handler, error_handler=error_handler)
