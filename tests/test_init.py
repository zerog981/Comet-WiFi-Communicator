"""Tests for the public package surface."""

import comet_wifi_communicator


class TestPublicApi:
    """The provisioning API is importable from the package root."""

    def test_all_names_resolve(self) -> None:
        """Every name in __all__ is an attribute of the package."""
        for name in comet_wifi_communicator.__all__:
            assert hasattr(comet_wifi_communicator, name), name

    def test_provision_is_the_same_object(self) -> None:
        """The root re-exports the function, not a copy."""
        from comet_wifi_communicator.provision import provision  # noqa: PLC0415

        assert comet_wifi_communicator.provision is provision
