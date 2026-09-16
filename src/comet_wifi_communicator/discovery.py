"""Finding out a thermostat's MAC address during setup.

The MAC address of the thermostat hotspot can be found in the ARP table. The address
used by the thermostat later is the hotspot's MAC minus one in the last byte.
"""

import ipaddress
import logging
import re
import shutil
import subprocess  # nosec B404
from pathlib import Path

from comet_wifi_communicator.provision import THERMOSTAT_IP, InvalidSettingsError

_LOGGER = logging.getLogger(__name__)

_PROC_NET_ARP = Path("/proc/net/arp")
"""ARP table on Linux, fall back to the ``arp`` command for other OS."""

_ARP_COMMAND_TIMEOUT = 5.0
_ARP_FLAG_COMPLETE = 0x2
_ARP_FIELD_COUNT = 4
# One or two hex digits per byte: macOS prints ``a:b:c:d:e:f`` without leading
# zeros, Windows separates the bytes with dashes.
_MAC_PATTERN = re.compile(r"\b[0-9a-f]{1,2}(?:[:-][0-9a-f]{1,2}){5}\b", re.IGNORECASE)
_UNUSABLE_MACS = frozenset({"00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"})


def normalize_mac(mac: str) -> str:
    """Return ``mac`` as six uppercase two-digit bytes separated by colons.

    :param mac: A MAC address with colons or dashes between the bytes.
    :return: The normalized address.
    """
    return ":".join(f"{int(byte, 16):02X}" for byte in re.split(r"[:-]", mac))


def thermostat_mac_from_hotspot(hotspot_mac: str) -> str:
    """Return the thermostat's own MAC address, derived from its hotspot.

    :param hotspot_mac: The MAC address of the hotspot.
    :return: The address the thermostat uses on the network, normalized.
    """
    mac_bytes = [int(byte, 16) for byte in normalize_mac(hotspot_mac).split(":")]
    mac_bytes[-1] = (mac_bytes[-1] - 1) % 256
    return ":".join(f"{byte:02X}" for byte in mac_bytes)


def _mac_from_proc(ip: str) -> str | None:
    """Look ``ip`` up in the Linux neighbour table."""
    try:
        table = _PROC_NET_ARP.read_text(encoding="ascii")
    except OSError:
        return None
    for line in table.splitlines()[1:]:
        fields = line.split()
        if len(fields) < _ARP_FIELD_COUNT or fields[0] != ip:
            continue
        if int(fields[2], 16) & _ARP_FLAG_COMPLETE:
            return fields[3]
    return None


def _mac_from_arp_command(ip: str) -> str | None:
    """Look ``ip`` up with the ``arp`` command (macOS, Windows, Linux net-tools)."""
    arp = shutil.which("arp")
    if arp is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603  # nosec B603
            [arp, "-a", ip],
            capture_output=True,
            text=True,
            check=False,
            timeout=_ARP_COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as err:
        _LOGGER.debug("Running %s failed: %s", arp, err)
        return None
    match = _MAC_PATTERN.search(result.stdout)
    return match.group(0) if match else None


def hotspot_mac(thermostat_ip: str = THERMOSTAT_IP) -> str | None:
    """Return the MAC address of the thermostat's hotspot, if this computer knows it.

    The address is taken from the ARP table, so this computer must be connected to the
    hotspot.

    :param thermostat_ip: The thermostat's address inside its hotspot.
    :return: The normalized MAC address, or ``None`` when it cannot be found.
    :raises InvalidSettingsError: If ``thermostat_ip`` is not an IP address.
    """
    try:
        thermostat_ip = str(ipaddress.ip_address(thermostat_ip))
    except ValueError as err:
        msg = f"{thermostat_ip!r} is not an IP address"
        raise InvalidSettingsError(msg) from err
    mac = _mac_from_proc(thermostat_ip) or _mac_from_arp_command(thermostat_ip)
    if mac is None:
        _LOGGER.debug("No neighbour table entry for %s", thermostat_ip)
        return None
    mac = normalize_mac(mac)
    return None if mac in _UNUSABLE_MACS else mac


def discover_thermostat_mac(thermostat_ip: str = THERMOSTAT_IP) -> str | None:
    """Return the MAC address of the thermostat.

    :param thermostat_ip: The thermostat's address inside its hotspot.
    :return: The thermostat's MAC address, or ``None`` when it cannot be found.
    :raises InvalidSettingsError: If ``thermostat_ip`` is not an IP address.
    """
    mac = hotspot_mac(thermostat_ip)
    return None if mac is None else thermostat_mac_from_hotspot(mac)
