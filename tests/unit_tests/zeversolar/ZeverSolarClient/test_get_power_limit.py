import pytest
import requests
import typing
from unittest.mock import call, Mock

from pytest_mock import MockFixture

from zeversolar import PowerLimitMode, ZeverSolarPowerLimitData
from zeversolar.exceptions import (
    ZeverSolarError,
    ZeverSolarHTTPError,
    ZeverSolarInvalidData,
    ZeverSolarPowerLimitNotSupported,
    ZeverSolarTimeout,
)

# adv.cgi response: one field per line; line 11 (0-indexed) = ac_value1, line 13 = ac_mode
_ADV_CGI_RESPONSE = "\n".join([
    "line0", "line1", "line2", "line3", "line4", "line5",
    "line6", "line7", "line8", "line9", "line10",
    "75",        # line 11 — ac_value1 (power limit %)
    "line12",
    "1",         # line 13 — ac_mode (1 = PERCENTAGE)
])


def test_get_power_limit(mocker: MockFixture, instance: Mock):
    patched_get = mocker.patch("zeversolar.requests.get")
    patched_get.return_value.text = _ADV_CGI_RESPONSE

    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)

    result = ZeverSolarClient.get_power_limit(self=fake.instance)

    patched_get.assert_called_once_with(
        url=f"http://{fake.instance.host}/adv.cgi",
        timeout=fake.instance._timeout,
    )
    assert result == ZeverSolarPowerLimitData(mode=PowerLimitMode.PERCENTAGE, limit_pct=75)


@pytest.mark.parametrize(
    argnames="requests_side_effect,response_status,expected_exception",
    argvalues=(
        (Exception, None, ZeverSolarError),
        (requests.exceptions.Timeout, None, ZeverSolarTimeout),
        (requests.exceptions.HTTPError, 404, ZeverSolarPowerLimitNotSupported),
        (requests.exceptions.HTTPError, 500, ZeverSolarHTTPError),
    ),
)
def test_get_power_limit_exception(
    mocker: MockFixture,
    requests_side_effect: type[Exception],
    response_status: typing.Optional[int],
    expected_exception: type[Exception],
    instance: Mock,
):
    patched_get = mocker.patch("zeversolar.requests.get")
    if response_status is None:
        patched_get.side_effect = [requests_side_effect]
    else:
        patched_get.return_value.raise_for_status.side_effect = [requests_side_effect]
        patched_get.return_value.status_code = response_status

    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)

    with pytest.raises(expected_exception):
        ZeverSolarClient.get_power_limit(self=fake.instance)


def test_get_power_limit_invalid_data_too_few_lines(mocker: MockFixture, instance: Mock):
    patched_get = mocker.patch("zeversolar.requests.get")
    patched_get.return_value.text = "too\nfew\nlines"

    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)

    with pytest.raises(ZeverSolarInvalidData):
        ZeverSolarClient.get_power_limit(self=fake.instance)


@pytest.mark.parametrize(
    argnames="bad_response",
    argvalues=(
        "\n".join(["x"] * 11 + ["not_a_number"] + ["x"] + ["1"]),  # ac_value1 not numeric
        "\n".join(["x"] * 11 + ["75"] + ["x"] + ["99"]),           # ac_mode not a valid PowerLimitMode
    ),
)
def test_get_power_limit_invalid_data_unparseable_fields(
    mocker: MockFixture,
    instance: Mock,
    bad_response: str,
):
    patched_get = mocker.patch("zeversolar.requests.get")
    patched_get.return_value.text = bad_response

    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)

    with pytest.raises(ZeverSolarInvalidData):
        ZeverSolarClient.get_power_limit(self=fake.instance)
