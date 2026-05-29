import threading
from unittest.mock import Mock, call

import pytest
from pytest_mock import MockFixture

from zeversolar import PowerLimitMode, ZeverSolarPowerLimitData, MINIMUM_LIMIT, RAMP_STEP, RAMP_RATE_UP, RAMP_RATE_DOWN


def _make_power_limit_data(limit_pct: int) -> ZeverSolarPowerLimitData:
    return ZeverSolarPowerLimitData(mode=PowerLimitMode.PERCENTAGE, limit_pct=limit_pct)


def _run_do_ramp(client_instance, limit_pct, ramp_rate=None, on_step=None, stop=None):
    """Call _do_ramp directly in the test thread with a fresh stop event."""
    from zeversolar import ZeverSolarClient
    stop = stop or threading.Event()
    ZeverSolarClient._do_ramp(
        self=client_instance,
        limit_pct=limit_pct,
        ramp_rate=ramp_rate,
        on_step=on_step,
        stop=stop,
    )


# --- set_power_limit: threading behaviour ---

def test_set_power_limit_returns_immediately(mocker: MockFixture, instance: Mock):
    """set_power_limit starts a thread and returns without waiting."""
    mocker.patch("zeversolar.threading.Thread")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)

    ZeverSolarClient.set_power_limit(self=fake.instance, limit_pct=50)
    # If we get here the call did not block


def test_set_power_limit_cancels_previous_ramp(mocker: MockFixture, instance: Mock):
    """A second call signals the first ramp's stop event before starting a new thread."""
    mocker.patch("zeversolar.threading.Thread")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    first_stop = threading.Event()
    fake.instance._ramp_stop = first_stop

    ZeverSolarClient.set_power_limit(self=fake.instance, limit_pct=50)

    assert first_stop.is_set()


# --- _do_ramp: ramp logic ---

def test_do_ramp_no_change(mocker: MockFixture, instance: Mock):
    """No writes when current == target."""
    mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(50)

    _run_do_ramp(fake.instance, limit_pct=50)

    fake.instance._write_power_limit.assert_not_called()


def test_do_ramp_ramp_up(mocker: MockFixture, instance: Mock):
    """Ramping up from 30% to 50% writes two 10% steps, waits RAMP_RATE_UP between them."""
    patched_wait = mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(30)

    _run_do_ramp(fake.instance, limit_pct=50)

    assert fake.instance._write_power_limit.call_args_list == [call(40), call(50)]
    patched_wait.assert_called_once_with(timeout=RAMP_RATE_UP)


def test_do_ramp_ramp_down(mocker: MockFixture, instance: Mock):
    """Ramping down from 80% to 60% writes two 10% steps, waits RAMP_RATE_DOWN between them."""
    patched_wait = mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(80)

    _run_do_ramp(fake.instance, limit_pct=60)

    assert fake.instance._write_power_limit.call_args_list == [call(70), call(60)]
    patched_wait.assert_called_once_with(timeout=RAMP_RATE_DOWN)


def test_do_ramp_ramp_rate_controls_step_size(mocker: MockFixture, instance: Mock):
    """ramp_rate=5 gives finer 5% steps."""
    mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(30)

    _run_do_ramp(fake.instance, limit_pct=50, ramp_rate=5)

    assert fake.instance._write_power_limit.call_args_list == [
        call(35), call(40), call(45), call(50)
    ]


def test_do_ramp_ramp_rate_100_jumps_directly(mocker: MockFixture, instance: Mock):
    """ramp_rate=100 results in a single write — no sleep."""
    patched_wait = mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(30)

    _run_do_ramp(fake.instance, limit_pct=80, ramp_rate=100)

    assert fake.instance._write_power_limit.call_args_list == [call(80)]
    patched_wait.assert_not_called()


def test_do_ramp_clamps_to_minimum(mocker: MockFixture, instance: Mock):
    """Target below MINIMUM_LIMIT is clamped."""
    mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(100)

    _run_do_ramp(fake.instance, limit_pct=0)

    last_call = fake.instance._write_power_limit.call_args_list[-1]
    assert last_call == call(MINIMUM_LIMIT)


def test_do_ramp_clamps_to_maximum(mocker: MockFixture, instance: Mock):
    """Target above 100 is clamped to 100."""
    mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(50)

    _run_do_ramp(fake.instance, limit_pct=200)

    last_call = fake.instance._write_power_limit.call_args_list[-1]
    assert last_call == call(100)


def test_do_ramp_on_step_called(mocker: MockFixture, instance: Mock):
    """on_step is called after each write with the new value."""
    mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(30)
    on_step = mocker.Mock()

    _run_do_ramp(fake.instance, limit_pct=50, on_step=on_step)

    assert on_step.call_args_list == [call(40), call(50)]


def test_do_ramp_write_failure_propagates(mocker: MockFixture, instance: Mock):
    """If _write_power_limit raises mid-ramp the exception propagates out of the thread."""
    mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    from zeversolar.exceptions import ZeverSolarError
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(30)
    fake.instance._write_power_limit.side_effect = ZeverSolarError("inverter gone")

    with pytest.raises(ZeverSolarError):
        _run_do_ramp(fake.instance, limit_pct=60)

    # Only attempted the first step before raising
    assert fake.instance._write_power_limit.call_count == 1


def test_do_ramp_stops_when_event_set(mocker: MockFixture, instance: Mock):
    """Ramp exits cleanly after the current step when stop event is set."""
    mocker.patch("zeversolar.threading.Event.wait")
    from zeversolar import ZeverSolarClient
    fake = mocker.Mock(instance=instance)
    fake.instance.get_power_limit.return_value = _make_power_limit_data(30)

    stop = threading.Event()

    def write_and_stop(val: int) -> None:
        # Simulate cancellation arriving after the first write
        stop.set()

    fake.instance._write_power_limit.side_effect = write_and_stop

    _run_do_ramp(fake.instance, limit_pct=60, stop=stop)

    # Only the first step (40%) was written; loop exited before writing 50% or 60%
    assert fake.instance._write_power_limit.call_args_list == [call(40)]
