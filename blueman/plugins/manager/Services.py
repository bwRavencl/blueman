from blueman.bluez.BlueZInterface import BlueZInterface
from blueman.bluez.Network import Network
from blueman.plugins.ManagerPlugin import ManagerPlugin
from gi.repository import Gtk

from blueman.Sdp import *
from blueman.Functions import *
from blueman.main.SignalTracker import SignalTracker
from blueman.gui.manager.ManagerProgressbar import ManagerProgressbar
from blueman.main.Config import Config
from blueman.main.AppletService import AppletService
from blueman.gui.MessageArea import MessageArea
from blueman.services import *

from blueman.Lib import rfcomm_list


def get_x_icon(icon_name, size):
    ic = get_icon(icon_name, size)
    x = get_icon("blueman-x", size)
    pixbuf = composite_icon(ic, [(x, 0, 0, 255)])

    return pixbuf


class Services(ManagerPlugin):
    connectable_uuids = [HID_SVCLASS_ID, AUDIO_SOURCE_SVCLASS_ID, AUDIO_SINK_SVCLASS_ID, HEADSET_SVCLASS_ID, HANDSFREE_SVCLASS_ID]

    def on_request_menu_items(self, manager_menu, device):
        items = []
        appl = AppletService()

        self.has_dun = False
        serial_items = []

        def add_menu_item(manager_menu, service, port_name=None, channel=None):
            if service.connected:
                item = create_menuitem(port_name or service.name, get_x_icon(service.icon, 16))
                port = channel and "/dev/rfcomm%d" % service.serial_port_id(channel) or None
                manager_menu.Signals.Handle("gobject", item, "activate", manager_menu.on_disconnect, service, port)
                items.append((item, service.priority + 100))
            else:
                item = create_menuitem(port_name or service.name, get_icon(service.icon, 16))
                if service.description:
                    item.props.tooltip_text = service.description
                manager_menu.Signals.Handle("gobject", item, "activate", manager_menu.on_connect, service)
                if service.group == 'serial':
                    serial_items.append(item)
                    if isinstance(service, DialupNetwork):
                        self.has_dun = True
                else:
                    items.append((item, service.priority))
            item.show()

        for service in device.get_services():
            if service.group == 'network':
                manager_menu.Signals.Handle("bluez", Network(device.get_object_path()),
                                            manager_menu.service_property_changed, "PropertyChanged")

            if isinstance(service, Input):
                manager_menu.Signals.Handle("bluez", device, manager_menu.service_property_changed, "PropertyChanged")

            for port in service.ports:
                add_menu_item(manager_menu, service, *port)
            else:
                add_menu_item(manager_menu, service)

                if service.group == 'serial':
                    for dev in rfcomm_list():
                        if dev["dst"] == device.Address and dev["state"] == "connected":
                            devname = _("Serial Port %s") % "rfcomm%d" % dev["id"]

                            item = create_menuitem(devname, get_x_icon("modem", 16))
                            manager_menu.Signals.Handle("gobject", item, "activate", manager_menu.on_disconnect, service, "/dev/rfcomm%d" % dev["id"])
                            items.append((item, 120))
                            item.show()

            if service.group == 'network' and service.connected:
                if "DhcpClient" in appl.QueryPlugins():
                    def renew(x):
                        appl.DhcpClient(Network(device.get_object_path()).get_properties()["Interface"])

                    item = create_menuitem(_("Renew IP Address"), get_icon("view-refresh", 16))
                    manager_menu.Signals.Handle("gobject", item, "activate", renew)
                    item.show()
                    items.append((item, 201))

        if self.has_dun and "PPPSupport" in appl.QueryPlugins():
            def open_settings(i, device):
                from blueman.gui.GsmSettings import GsmSettings

                d = GsmSettings(device.Address)
                d.run()
                d.destroy()

            item = Gtk.SeparatorMenuItem()
            item.show()
            serial_items.append(item)

            item = create_menuitem(_("Dialup Settings"), get_icon("gtk-preferences", 16))
            serial_items.append(item)
            item.show()
            manager_menu.Signals.Handle("gobject", item, "activate", open_settings, device)

        if len(serial_items) > 1:
            sub = Gtk.Menu()
            sub.show()

            item = create_menuitem(_("Serial Ports"), get_icon("modem", 16))
            item.set_submenu(sub)
            item.show()
            items.append((item, 90))

            for item in serial_items:
                sub.append(item)
        else:
            for item in serial_items:
                items.append((item, 80))

        return items
