from unittest.mock import call

import pytest
from pytest_mock import MockFixture


def test_power_off_m10(mocker: MockFixture):
    """M10: delegates to ctrl_power and returns PowerMode."""
    from zeversolar import ZeverSolarClient, PowerMode
    fake = mocker.Mock(instance=mocker.Mock(spec=ZeverSolarClient))
    fake.instance._is_m10.return_value = True

    result = ZeverSolarClient.power_off(self=fake.instance)

    fake.instance.assert_has_calls(calls=[call.ctrl_power(mode=PowerMode.OFF)])
    assert result is fake.instance.ctrl_power.return_value


def test_power_off_m11(mocker: MockFixture):
    """M11: ramps to MINIMUM_LIMIT via set_power_limit, returns None."""
    from zeversolar import ZeverSolarClient, MINIMUM_LIMIT
    fake = mocker.Mock(instance=mocker.Mock(spec=ZeverSolarClient))
    fake.instance._is_m10.return_value = False

    result = ZeverSolarClient.power_off(self=fake.instance)

    fake.instance.assert_has_calls(calls=[call.set_power_limit(MINIMUM_LIMIT)])
    assert result is None
