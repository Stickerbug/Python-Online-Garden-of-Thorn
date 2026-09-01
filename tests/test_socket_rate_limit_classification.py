from unittest import mock

import app as gtn


def test_skin_look_uses_an_isolated_rate_budget():
    sid = 'skin-rate-budget-test'
    gtn.players[sid] = {'user_id': 88001}
    calls = []

    def fake_rate_limiter(key, **kwargs):
        calls.append((key, kwargs))
        return ':all' not in key

    try:
        with mock.patch.object(gtn, 'rate_limiter', side_effect=fake_rate_limiter):
            assert gtn._socket_rate_allowed(sid, 'skin_look') is True
            assert gtn._socket_rate_allowed(sid, 'invite') is False

        skin_keys = [key for key, _ in calls if 'skin_look' in key]
        assert skin_keys == [
            f'socket:sid:{sid}:skin_look',
            'socket:user:88001:skin_look',
            'socket:server:skin_look',
        ]
        assert not any(':all' in key for key in skin_keys)
    finally:
        gtn.players.pop(sid, None)


def test_rate_limit_rejection_does_not_count_as_illegal_operation():
    sid = 'ordinary-rate-reject-test'
    gtn.players[sid] = {'user_id': 88002}
    try:
        with (
            mock.patch.object(gtn, 'request', mock.Mock(sid=sid)),
            mock.patch.object(gtn, '_socket_rate_allowed', return_value=False),
            mock.patch.object(gtn, '_security_rate_limited') as record_rate,
            mock.patch.object(gtn, '_security_illegal') as record_illegal,
            mock.patch.object(gtn, 'emit') as emit,
        ):
            assert gtn.socket_guard('invite', {'target_sid': 'target'}) is None

        record_rate.assert_called_once_with(sid, 'invite')
        record_illegal.assert_not_called()
        emit.assert_called_once_with('server_error', {
            'message': '操作过于频繁',
            'code': 'ACTION_TOO_FAST',
        })
    finally:
        gtn.players.pop(sid, None)


def test_skin_look_rate_rejection_is_silent_and_not_illegal():
    sid = 'skin-silent-rate-reject-test'
    gtn.players[sid] = {'user_id': 88003}
    try:
        with (
            mock.patch.object(gtn, 'request', mock.Mock(sid=sid)),
            mock.patch.object(gtn, '_socket_rate_allowed', return_value=False),
            mock.patch.object(gtn, '_security_rate_limited') as record_rate,
            mock.patch.object(gtn, '_security_illegal') as record_illegal,
            mock.patch.object(gtn, 'emit') as emit,
        ):
            assert gtn.socket_guard('skin_look', {'x': 1, 'y': 0}, require_player=False, emit_error=False) is None

        record_rate.assert_called_once_with(sid, 'skin_look')
        record_illegal.assert_not_called()
        emit.assert_not_called()
    finally:
        gtn.players.pop(sid, None)


def test_skin_look_before_reconnect_login_is_ignored_without_illegal_strike():
    sid = 'skin-reconnect-race-test'
    gtn.players.pop(sid, None)
    with (
        mock.patch.object(gtn, 'request', mock.Mock(sid=sid)),
        mock.patch.object(gtn, '_socket_rate_allowed', return_value=True),
        mock.patch.object(gtn, '_security_illegal') as record_illegal,
    ):
        assert gtn.on_skin_look({'x': 0.5, 'y': -0.5}) is None

    record_illegal.assert_not_called()


def test_low_severity_validation_is_logged_without_kick_counter():
    sid = 'low-severity-validation-test'
    with (
        mock.patch.object(gtn, 'request', mock.Mock(sid=sid)),
        mock.patch.object(gtn, 'record_illegal_operation') as record_illegal,
        mock.patch.object(gtn, '_security_record') as record_event,
    ):
        assert gtn._security_illegal(
            sid,
            'chat',
            'message is too long',
            severity='low',
            emit_error=False,
        ) is False

    record_illegal.assert_not_called()
    extra = record_event.call_args.kwargs['extra']
    assert extra['hard_illegal'] is False
    assert extra['counts_toward_kick'] is False
    assert extra['illegal_count'] == 0


def test_medium_severity_validation_still_counts_toward_kick():
    sid = 'hard-validation-test'
    with (
        mock.patch.object(gtn, 'request', mock.Mock(sid=sid)),
        mock.patch.object(gtn, 'record_illegal_operation', return_value=(1, False)) as record_illegal,
        mock.patch.object(gtn, '_security_record') as record_event,
    ):
        assert gtn._security_illegal(
            sid,
            'play_card',
            'instance id format is invalid',
            severity='medium',
            emit_error=False,
        ) is False

    record_illegal.assert_called_once()
    extra = record_event.call_args.kwargs['extra']
    assert extra['hard_illegal'] is True
    assert extra['counts_toward_kick'] is True
    assert extra['illegal_count'] == 1
