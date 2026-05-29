from unittest.mock import call

import pytest
from pytest_mock import MockFixture


def test_power_on_m10(mocker: MockFixture):
    """M10: delegates to ctrl_power and returns PowerMode."""
    from zeversolar import ZeverSolarClient, PowerMode
    fake = mocker.Mock(instance=mocker.Mock(spec=ZeverSolarClient))
    fake.instance._is_m10.return_value = True

    result = ZeverSolarClient.power_on(self=fake.instance)

    fake.instance.assert_has_calls(calls=[call.ctrl_power(mode=PowerMode.ON)])
    assert result is fake.instance.ctrl_power.return_value


def test_power_on_m11(mocker: MockFixture):
    """M11: ramps to 100% via set_power_limit, returns None."""
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=mocker.Mock(spec=ZeverSolarClient))
    fake.instance._is_m10.return_value = False

    result = ZeverSolarClient.power_on(self=fake.instance)

    fake.instance.assert_has_calls(calls=[call.set_power_limit(100)])
    assert result is None
