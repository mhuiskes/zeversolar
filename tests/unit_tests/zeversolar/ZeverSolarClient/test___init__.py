import threading
from unittest.mock import call

import pytest
import pytest_mock


@pytest.mark.parametrize("host", ("mock_host", "http://mock_host", "https://mock_host"))
def test___init__(mocker: pytest_mock.MockerFixture, host: str):
    fake_urllib = mocker.patch("zeversolar.urllib.parse")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(**{
        "instance": mocker.Mock(spec=ZeverSolarClient),
    })

    ZeverSolarClient.__init__(self=fake.instance, host=host)

    if "http" not in host:
        host = f"http://{host}"
    assert fake.instance.host == fake_urllib.urlparse.return_value.netloc.strip.return_value
    assert fake.instance._timeout == 10
    assert fake.instance._serial_number is None
    assert fake.instance._hardware_version is None
    assert isinstance(fake.instance._ramp_stop, threading.Event)
    assert type(fake.instance._ramp_lock) is type(threading.Lock())
    fake_urllib.assert_has_calls(calls=[
        call.urlparse(url=host),
        call.urlparse().netloc.strip("/"),
    ])


@pytest.mark.parametrize(
    argnames=("hardware_version", "expected"),
    argvalues=(
        ("M10", True),
        ("M10A", True),   # variant M10 hardware still matches
        ("M11", False),
        ("M11A", False),
        ("", False),
    ),
)
def test_is_m10(mocker: pytest_mock.MockerFixture, hardware_version: str, expected: bool):
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=mocker.Mock(spec=ZeverSolarClient))
    fake.instance._hardware_version = hardware_version

    result = ZeverSolarClient._is_m10(self=fake.instance)

    assert result is expected
    fake.instance.get_data.assert_not_called()


def test_is_m10_fetches_hardware_version_when_unknown(mocker: pytest_mock.MockerFixture):
    """If _hardware_version is None, get_data() is called to populate it."""
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=mocker.Mock(spec=ZeverSolarClient))
    fake.instance._hardware_version = None

    def populate_hardware_version():
        fake.instance._hardware_version = "M11"

    fake.instance.get_data.side_effect = populate_hardware_version

    result = ZeverSolarClient._is_m10(self=fake.instance)

    fake.instance.get_data.assert_called_once()
    assert result is False
