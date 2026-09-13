"""The ``comet-wifi-communicator`` command."""

import argparse
import getpass
import logging
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version

from comet_wifi_communicator.provision import (
    DEFAULT_MQTT_PORT,
    THERMOSTAT_IP,
    THERMOSTAT_PORT,
    ProvisioningError,
    provision,
)

_LOGGER = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INTERRUPTED = 130

PROG = "comet-wifi-communicator"
DESCRIPTION = "Tools for Comet WiFi thermostats running against your own MQTT broker."
SETUP_HELP = "Point a thermostat at your Wi-Fi network and your own MQTT broker."
SETUP_EPILOG = """\
Before running this command:
  1. Reset the thermostat: with a pin, press and hold the reset button in the
     battery tray until the display turns off, release it, then remove and
     re-insert the batteries. After a few seconds the display shows "PA" and
     the Wi-Fi symbol blinks.
  2. Connect this computer to the thermostat's Wi-Fi hotspot "Comet Wifi"
     (password 11223344).
Once configured, the thermostat closes the hotspot and joins your network.
"""


def _package_version() -> str:
    """Return the installed version, or a placeholder when run from source."""
    try:
        return version("comet-wifi-communicator")
    except PackageNotFoundError:
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser with its subcommands."""
    parser = argparse.ArgumentParser(prog=PROG, description=DESCRIPTION)
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_package_version()}"
    )
    subcommands = parser.add_subparsers(title="commands", required=True)

    setup = subcommands.add_parser(
        "setup",
        help=SETUP_HELP,
        description=SETUP_HELP,
        epilog=SETUP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    setup.set_defaults(run=_run_setup)
    setup.add_argument(
        "--wifi-ssid",
        required=True,
        help="Wi-Fi network the thermostat should join.",
    )
    setup.add_argument(
        "--wifi-password",
        help=(
            "Password of the Wi-Fi network the thermostat should join. Prompted for"
            "when omitted (keeps it out of the shell history). Pass an empty string"
            "for an open network."
        ),
    )
    setup.add_argument(
        "--mqtt-server-ip",
        required=True,
        help="IPv4 address of the MQTT broker (host names are not supported).",
    )
    setup.add_argument(
        "--mqtt-server-port",
        type=int,
        default=DEFAULT_MQTT_PORT,
        help="TCP port of the MQTT broker (default: %(default)s).",
    )
    setup.add_argument(
        "--thermostat-ip",
        default=THERMOSTAT_IP,
        help="Address of the thermostat inside its hotspot (default: %(default)s).",
    )
    setup.add_argument(
        "--thermostat-port",
        type=int,
        default=THERMOSTAT_PORT,
        help="Port the thermostat listens on (default: %(default)s).",
    )
    setup.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show debug output and full error details.",
    )
    return parser


def _configure_logging(*, verbose: bool) -> None:
    """Send progress messages to stderr, one line each."""
    logging.basicConfig(stream=sys.stderr, format="%(message)s")
    logging.getLogger("comet_wifi_communicator").setLevel(
        logging.DEBUG if verbose else logging.INFO
    )


def _run_setup(args: argparse.Namespace) -> int:
    """Run the ``setup`` subcommand.

    :param args: The parsed arguments.
    :return: The process exit code.
    """
    if args.wifi_password is not None:
        wifi_password: str = args.wifi_password
    else:
        try:
            wifi_password = getpass.getpass(
                "Wi-Fi password (leave empty for an open network): "
            )
        except (KeyboardInterrupt, EOFError):
            _LOGGER.warning("Aborted.")
            return EXIT_INTERRUPTED

    try:
        provision(
            args.wifi_ssid,
            wifi_password,
            args.mqtt_server_ip,
            args.mqtt_server_port,
            thermostat_address=(args.thermostat_ip, args.thermostat_port),
        )
    except ProvisioningError as err:
        _LOGGER.error("%s", err, exc_info=args.verbose)  # noqa: TRY400
        return EXIT_FAILURE
    except KeyboardInterrupt:
        _LOGGER.warning("Aborted.")
        return EXIT_INTERRUPTED

    _LOGGER.info(
        "Done. The thermostat now joins %r and connects to the MQTT broker at %s:%d.",
        args.wifi_ssid,
        args.mqtt_server_ip,
        args.mqtt_server_port,
    )
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command.

    :param argv: Arguments.
    :return: The process exit code.
    """
    args = build_parser().parse_args(argv)
    _configure_logging(verbose=args.verbose)
    exit_code: int = args.run(args)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
