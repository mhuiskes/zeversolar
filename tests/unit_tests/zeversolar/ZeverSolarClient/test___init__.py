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
        (None, False),    # not yet detected
        ("", False),
    ),
)
def test_is_m10(mocker: pytest_mock.MockerFixture, hardware_version: str | None, expected: bool):
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=mocker.Mock(spec=ZeverSolarClient))
    fake.instance._hardware_version = hardware_version

    result = ZeverSolarClient._is_m10(self=fake.instance)

    assert result is expected
