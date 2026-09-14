"""Tests for the MAC address lookup."""

import subprocess
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from comet_wifi_communicator import discovery
from comet_wifi_communicator.discovery import (
    discover_thermostat_mac,
    hotspot_mac,
    normalize_mac,
    thermostat_mac_from_hotspot,
)
from comet_wifi_communicator.provision import InvalidSettingsError

HOTSPOT_MAC = "A4:CF:12:34:56:79"
THERMOSTAT_MAC = "A4:CF:12:34:56:78"

PROC_NET_ARP = """\
IP address       HW type     Flags       HW address            Mask     Device
192.168.178.1    0x1         0x2         11:22:33:44:55:66     *        wlp3s0
10.0.0.1         0x1         0x2         a4:cf:12:34:56:79     *        wlp3s0
"""

PROC_NET_ARP_INCOMPLETE = """\
IP address       HW type     Flags       HW address            Mask     Device
10.0.0.1         0x1         0x0         00:00:00:00:00:00     *        wlp3s0
"""


@pytest.fixture
def proc_net_arp(tmp_path: Path) -> Iterator[Path]:
    """Point the module at the ARP table file under ``tmp_path``."""
    table = tmp_path / "arp"
    with patch.object(discovery, "_PROC_NET_ARP", table):
        yield table


@pytest.fixture
def arp_command() -> Iterator[MagicMock]:
    """Replace the ``arp`` command. ``return_value.stdout`` is its output."""
    with (
        patch("comet_wifi_communicator.discovery.shutil.which") as which,
        patch("comet_wifi_communicator.discovery.subprocess.run") as run,
    ):
        which.return_value = "/usr/sbin/arp"
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        yield run


class TestNormalizeMac:
    """Tests for the address normalization."""

    @pytest.mark.parametrize(
        "mac",
        [
            "A4:CF:12:34:56:79",
            "a4:cf:12:34:56:79",
            "A4-CF-12-34-56-79",
        ],
    )
    def test_separators_and_case(self, mac: str) -> None:
        """Colons and dashes, upper and lower case all normalize the same."""
        assert normalize_mac(mac) == HOTSPOT_MAC

    def test_single_digit_bytes(self) -> None:
        """Bytes below 0x10 come with one digit on macOS."""
        assert normalize_mac("a:b:c:d:e:f") == "0A:0B:0C:0D:0E:0F"


class TestThermostatMacFromHotspot:
    """Tests for the hotspot-to-thermostat derivation."""

    def test_last_byte_minus_one(self) -> None:
        """The thermostat's address is the hotspot's minus one in the last byte."""
        assert thermostat_mac_from_hotspot(HOTSPOT_MAC) == THERMOSTAT_MAC

    def test_last_byte_wraps(self) -> None:
        """Only the last byte changes, wrapping from 00 to FF."""
        assert thermostat_mac_from_hotspot("A4:CF:12:34:56:00") == "A4:CF:12:34:56:FF"

    def test_input_is_normalized(self) -> None:
        """Dashes and lower case are accepted."""
        assert thermostat_mac_from_hotspot("a4-cf-12-34-56-79") == THERMOSTAT_MAC


class TestHotspotMac:
    """Tests for the ARP table lookup."""

    def test_from_proc(self, proc_net_arp: Path, arp_command: MagicMock) -> None:
        """On Linux the address comes from /proc/net/arp."""
        proc_net_arp.write_text(PROC_NET_ARP)

        assert hotspot_mac("10.0.0.1") == HOTSPOT_MAC

        arp_command.assert_not_called()

    @pytest.mark.usefixtures("arp_command")
    def test_proc_other_ip(self, proc_net_arp: Path) -> None:
        """Another thermostat address is looked up, not the default."""
        proc_net_arp.write_text(PROC_NET_ARP)

        assert hotspot_mac("192.168.178.1") == "11:22:33:44:55:66"

    def test_proc_incomplete_entry(
        self, proc_net_arp: Path, arp_command: MagicMock
    ) -> None:
        """An unresolved entry is skipped and the command is tried."""
        proc_net_arp.write_text(PROC_NET_ARP_INCOMPLETE)

        assert hotspot_mac("10.0.0.1") is None

        arp_command.assert_called_once()

    def test_proc_missing_entry(
        self, proc_net_arp: Path, arp_command: MagicMock
    ) -> None:
        """Without an entry the command is tried."""
        proc_net_arp.write_text(PROC_NET_ARP)

        assert hotspot_mac("10.0.0.2") is None

        arp_command.assert_called_once()

    @pytest.mark.parametrize(
        "output",
        [
            "? (10.0.0.1) at a4:cf:12:34:56:79 [ether] on wlan0\n",
            "? (10.0.0.1) at a4:cf:12:34:56:79 on en0 ifscope [ethernet]\n",
            (
                "\nInterface: 10.0.0.2 --- 0x5\n"
                "  Internet Address      Physical Address      Type\n"
                "  10.0.0.1              a4-cf-12-34-56-79     dynamic\n"
            ),
        ],
        ids=["linux", "macos", "windows"],
    )
    @pytest.mark.usefixtures("proc_net_arp")
    def test_from_arp_command(self, arp_command: MagicMock, output: str) -> None:
        """Without /proc/net/arp the ``arp -a`` output is parsed."""
        arp_command.return_value.stdout = output

        assert hotspot_mac("10.0.0.1") == HOTSPOT_MAC

        assert arp_command.call_args.args[0] == ["/usr/sbin/arp", "-a", "10.0.0.1"]

    @pytest.mark.usefixtures("proc_net_arp")
    def test_arp_command_single_digit_bytes(self, arp_command: MagicMock) -> None:
        """Leading zeros are omitted on macOS."""
        arp_command.return_value.stdout = "? (10.0.0.1) at 4:f:12:34:56:9 on en0\n"

        assert hotspot_mac("10.0.0.1") == "04:0F:12:34:56:09"

    @pytest.mark.parametrize(
        "output",
        [
            "? (10.0.0.1) at (incomplete) on wlan0\n",
            "No ARP Entries Found.\n",
            "",
        ],
    )
    @pytest.mark.usefixtures("proc_net_arp")
    def test_arp_command_no_entry(self, arp_command: MagicMock, output: str) -> None:
        """Output without an address gives None."""
        arp_command.return_value.stdout = output

        assert hotspot_mac("10.0.0.1") is None

    @pytest.mark.parametrize(
        "error",
        [
            OSError("permission denied"),
            subprocess.TimeoutExpired(["arp"], 5.0),
        ],
    )
    @pytest.mark.usefixtures("proc_net_arp")
    def test_arp_command_fails(self, arp_command: MagicMock, error: Exception) -> None:
        """A failing command gives None."""
        arp_command.side_effect = error

        assert hotspot_mac("10.0.0.1") is None

    @pytest.mark.usefixtures("proc_net_arp")
    def test_arp_command_missing(self) -> None:
        """Without the command there is nothing to fall back to."""
        with patch("comet_wifi_communicator.discovery.shutil.which") as which:
            which.return_value = None

            assert hotspot_mac("10.0.0.1") is None

    @pytest.mark.parametrize("ip", ["-d", "thermostat.local", "", "10.0.0.1 -d"])
    def test_not_an_ip(self, arp_command: MagicMock, ip: str) -> None:
        """Anything but an IP address is rejected before it reaches the command."""
        with pytest.raises(InvalidSettingsError, match="not an IP address"):
            hotspot_mac(ip)

        arp_command.assert_not_called()

    @pytest.mark.parametrize("mac", ["00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"])
    @pytest.mark.usefixtures("proc_net_arp")
    def test_unusable_address(self, arp_command: MagicMock, mac: str) -> None:
        """The zero and the broadcast address are not a hotspot."""
        arp_command.return_value.stdout = f"? (10.0.0.1) at {mac} on en0\n"

        assert hotspot_mac("10.0.0.1") is None


class TestDiscoverThermostatMac:
    """Tests for the combined lookup."""

    @pytest.mark.usefixtures("arp_command")
    def test_found(self, proc_net_arp: Path) -> None:
        """The derived thermostat address is returned."""
        proc_net_arp.write_text(PROC_NET_ARP)

        assert discover_thermostat_mac("10.0.0.1") == THERMOSTAT_MAC

    @pytest.mark.usefixtures("arp_command")
    def test_default_ip(self, proc_net_arp: Path) -> None:
        """The default is the thermostat's hotspot address."""
        proc_net_arp.write_text(PROC_NET_ARP)

        assert discover_thermostat_mac() == THERMOSTAT_MAC

    @pytest.mark.usefixtures("proc_net_arp", "arp_command")
    def test_not_found(self) -> None:
        """None if the ARP table has nothing."""
        assert discover_thermostat_mac() is None
