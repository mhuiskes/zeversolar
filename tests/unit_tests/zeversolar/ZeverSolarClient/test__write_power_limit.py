import pytest
import requests
from unittest.mock import call, Mock

from pytest_mock import MockFixture

from zeversolar.exceptions import ZeverSolarError, ZeverSolarHTTPError, ZeverSolarHTTPNotFound, ZeverSolarTimeout


@pytest.mark.parametrize(
    argnames=("hardware_version", "expected_endpoint"),
    argvalues=(
        ("M11", "pwrlim.cgi"),
        ("M10", "adv.cgi"),
        (None, "pwrlim.cgi"),  # unknown hardware defaults to M11 endpoint
    ),
)
def test_write_power_limit_endpoint_selection(
    mocker: MockFixture,
    instance: Mock,
    hardware_version: str | None,
    expected_endpoint: str,
):
    patched_post = mocker.patch("zeversolar.requests.post")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance._is_m10.return_value = hardware_version == "M10"

    ZeverSolarClient._write_power_limit(self=fake.instance, limit_pct=75)

    patched_post.assert_called_once_with(
        url=f"http://{fake.instance.host}/{expected_endpoint}",
        data={
            "enlim": "on",
            "ac_sys": "0",
            "ac_mode": "1",
            "ac_value1": "75",
            "ac_value2": "0",
            "em_ml": "0",
            "ac_value3": "60",
            "drm_sp": "16.67",
        },
        timeout=fake.instance._timeout,
    )


def test_write_power_limit_connection_closed_is_success(mocker: MockFixture, instance: Mock):
    """Inverter closes TCP connection after processing — not an error."""
    patched_post = mocker.patch("zeversolar.requests.post")
    patched_post.side_effect = requests.exceptions.ConnectionError
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance._is_m10.return_value = False

    ZeverSolarClient._write_power_limit(self=fake.instance, limit_pct=75)  # must not raise


@pytest.mark.parametrize(
    argnames="requests_side_effect,response_status,expected_exception",
    argvalues=(
        (Exception, None, ZeverSolarError),
        (requests.exceptions.Timeout, None, ZeverSolarTimeout),
        (requests.exceptions.HTTPError, 404, ZeverSolarHTTPNotFound),
        (requests.exceptions.HTTPError, 500, ZeverSolarHTTPError),
    ),
)
def test_write_power_limit_exception(
    mocker: MockFixture,
    requests_side_effect: type[Exception],
    response_status: int | None,
    expected_exception: type[Exception],
    instance: Mock,
):
    patched_post = mocker.patch("zeversolar.requests.post")
    if response_status is None:
        patched_post.side_effect = [requests_side_effect]
    else:
        patched_post.return_value.raise_for_status.side_effect = [requests_side_effect]
        patched_post.return_value.status_code = response_status

    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance._is_m10.return_value = False

    with pytest.raises(expected_exception):
        ZeverSolarClient._write_power_limit(self=fake.instance, limit_pct=75)
