"""Tests for the ``comet-wifi-communicator`` command."""

import logging
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from comet_wifi_communicator.cli import (
    EXIT_FAILURE,
    EXIT_INTERRUPTED,
    EXIT_OK,
    main,
)
from comet_wifi_communicator.provision import (
    THERMOSTAT_ADDRESS,
    InvalidSettingsError,
    ThermostatUnreachableError,
)

REQUIRED_ARGS = [
    "setup",
    "--wifi-ssid",
    "MyWiFi",
    "--wifi-password",
    "s3cret",
    "--mqtt-server-ip",
    "192.168.178.2",
]


@pytest.fixture
def fake_provision() -> Iterator[MagicMock]:
    """Replace the provisioning call so nothing is sent."""
    with patch("comet_wifi_communicator.cli.provision") as mock:
        yield mock


@pytest.fixture
def fake_getpass() -> Iterator[MagicMock]:
    """Replace the interactive password prompt."""
    with patch("comet_wifi_communicator.cli.getpass.getpass") as mock:
        yield mock


@pytest.fixture(autouse=True)
def fake_discovery() -> Iterator[MagicMock]:
    """Replace the MAC lookup. It finds nothing unless a test says otherwise."""
    with patch("comet_wifi_communicator.cli.discover_thermostat_mac") as mock:
        mock.return_value = None
        yield mock


@pytest.fixture(autouse=True)
def reset_log_level() -> Iterator[None]:
    """Undo the level ``main`` sets on the package logger."""
    yield
    logging.getLogger("comet_wifi_communicator").setLevel(logging.NOTSET)


class TestArguments:
    """Tests for argument handling."""

    def test_all_arguments(self, fake_provision: MagicMock) -> None:
        """Every option reaches the provisioning call."""
        code = main(
            [
                *REQUIRED_ARGS,
                "--mqtt-server-port",
                "8883",
                "--thermostat-ip",
                "192.168.4.1",
                "--thermostat-port",
                "5000",
            ]
        )

        assert code == EXIT_OK
        fake_provision.assert_called_once_with(
            "MyWiFi",
            "s3cret",
            "192.168.178.2",
            8883,
            thermostat_address=("192.168.4.1", 5000),
        )

    def test_defaults(self, fake_provision: MagicMock) -> None:
        """The MQTT port and the thermostat address have defaults."""
        assert main(REQUIRED_ARGS) == EXIT_OK

        fake_provision.assert_called_once_with(
            "MyWiFi",
            "s3cret",
            "192.168.178.2",
            1883,
            thermostat_address=THERMOSTAT_ADDRESS,
        )

    def test_empty_password(self, fake_provision: MagicMock) -> None:
        """An empty password can be given explicitly for an open network."""
        argv = [arg if arg != "s3cret" else "" for arg in REQUIRED_ARGS]

        assert main(argv) == EXIT_OK

        assert fake_provision.call_args.args[1] == ""

    def test_password_prompt(
        self, fake_provision: MagicMock, fake_getpass: MagicMock
    ) -> None:
        """Without --wifi-password the password is prompted for."""
        fake_getpass.return_value = "typed"
        argv = [
            arg for arg in REQUIRED_ARGS if arg not in ("--wifi-password", "s3cret")
        ]

        assert main(argv) == EXIT_OK

        fake_getpass.assert_called_once()
        assert "password" in fake_getpass.call_args.args[0]
        assert fake_provision.call_args.args[1] == "typed"

    @pytest.mark.parametrize("error", [KeyboardInterrupt(), EOFError()])
    def test_prompt_aborted(
        self,
        fake_provision: MagicMock,
        fake_getpass: MagicMock,
        error: BaseException,
    ) -> None:
        """Interrupting the prompt exits without sending anything."""
        fake_getpass.side_effect = error
        argv = [
            arg for arg in REQUIRED_ARGS if arg not in ("--wifi-password", "s3cret")
        ]

        assert main(argv) == EXIT_INTERRUPTED

        fake_provision.assert_not_called()

    @pytest.mark.parametrize(
        ("argv", "match"),
        [
            ([], "usage: comet-wifi-communicator"),
            (["bad_subcommand"], "usage: comet-wifi-communicator"),
            (["setup"], "usage: comet-wifi-communicator setup"),
            (
                ["setup", "--wifi-ssid", "MyWiFi"],
                "usage: comet-wifi-communicator setup",
            ),
            ([*REQUIRED_ARGS, "--mqtt-server-port", "abc"], "invalid int value"),
        ],
    )
    def test_usage_error(
        self,
        fake_provision: MagicMock,
        argv: list[str],
        match: str,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A missing subcommand or bad arguments exit with argparse's usage error."""
        with pytest.raises(SystemExit) as info:
            main(argv)

        assert info.value.code == 2
        assert match in capsys.readouterr().err
        fake_provision.assert_not_called()

    def test_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """--version prints the program name and version."""
        with pytest.raises(SystemExit) as info:
            main(["--version"])

        assert info.value.code == 0
        assert capsys.readouterr().out.startswith("comet-wifi-communicator ")

    def test_help_lists_setup(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The top-level help lists the subcommand."""
        with pytest.raises(SystemExit) as info:
            main(["--help"])

        assert info.value.code == 0
        assert "setup" in capsys.readouterr().out

    def test_setup_help_mentions_the_hotspot(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """``setup --help`` carries the reset and hotspot instructions."""
        with pytest.raises(SystemExit) as info:
            main(["setup", "--help"])

        assert info.value.code == 0
        out = capsys.readouterr().out
        assert "Comet Wifi" in out
        assert "11223344" in out


class TestOutcome:
    """Tests for the exit code and the messages."""

    @pytest.mark.usefixtures("fake_provision")
    def test_success_message(self, caplog: pytest.LogCaptureFixture) -> None:
        """Success is reported with the network and the broker."""
        with caplog.at_level(logging.INFO):
            assert main(REQUIRED_ARGS) == EXIT_OK

        assert "192.168.178.2:1883" in caplog.text
        assert "'MyWiFi'" in caplog.text

    @pytest.mark.usefixtures("fake_provision")
    def test_mac_reported(
        self, fake_discovery: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """The thermostat's MAC address is looked up and reported after success."""
        fake_discovery.return_value = "A4:CF:12:34:56:78"

        with caplog.at_level(logging.INFO):
            assert main([*REQUIRED_ARGS, "--thermostat-ip", "192.168.4.1"]) == EXIT_OK

        fake_discovery.assert_called_once_with("192.168.4.1")
        assert "A4:CF:12:34:56:78" in caplog.text

    @pytest.mark.usefixtures("fake_provision")
    def test_mac_unknown(self, caplog: pytest.LogCaptureFixture) -> None:
        """Without an address the user is pointed at the router."""
        with caplog.at_level(logging.INFO):
            assert main(REQUIRED_ARGS) == EXIT_OK

        assert "router" in caplog.text

    def test_no_lookup_after_failure(
        self, fake_provision: MagicMock, fake_discovery: MagicMock
    ) -> None:
        """A failed setup does not report an address."""
        fake_provision.side_effect = ThermostatUnreachableError("unreachable")

        assert main(REQUIRED_ARGS) == EXIT_FAILURE

        fake_discovery.assert_not_called()

    @pytest.mark.parametrize(
        "error",
        [
            InvalidSettingsError("The Wi-Fi SSID must not be empty."),
            ThermostatUnreachableError("Could not deliver the configuration."),
        ],
    )
    def test_provisioning_error(
        self,
        fake_provision: MagicMock,
        caplog: pytest.LogCaptureFixture,
        error: Exception,
    ) -> None:
        """A provisioning error is reported without a traceback."""
        fake_provision.side_effect = error

        with caplog.at_level(logging.INFO):
            assert main(REQUIRED_ARGS) == EXIT_FAILURE

        assert str(error) in caplog.text
        assert "Traceback" not in caplog.text

    def test_verbose_shows_the_traceback(
        self, fake_provision: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """With --verbose the full error details are included."""
        fake_provision.side_effect = ThermostatUnreachableError("timed out")

        with caplog.at_level(logging.DEBUG):
            assert main([*REQUIRED_ARGS, "--verbose"]) == EXIT_FAILURE

        assert "Traceback" in caplog.text
        assert logging.getLogger("comet_wifi_communicator").level == logging.DEBUG

    def test_interrupted_while_sending(self, fake_provision: MagicMock) -> None:
        """Ctrl-C during the transfer exits with the conventional code."""
        fake_provision.side_effect = KeyboardInterrupt()

        assert main(REQUIRED_ARGS) == EXIT_INTERRUPTED
