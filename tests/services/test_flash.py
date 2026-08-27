import base64
import http.cookies
import json

from starlette.requests import Request
from starlette.responses import Response

from app.services import flash


def _decode(raw: str):
    return json.loads(base64.urlsafe_b64decode(raw.encode()))


def _cookie_value(response: Response) -> str:
    cookie = http.cookies.SimpleCookie()
    cookie.load(response.headers['set-cookie'])
    return cookie['flash'].value


def _request_with_cookie_from(response: Response) -> Request:
    # Reuse the exact Set-Cookie encoding flash.send produced, rather than
    # hand-building a Cookie header.
    name_value = response.headers['set-cookie'].split(';', 1)[0]
    scope = {'type': 'http', 'headers': [(b'cookie', name_value.encode())]}
    return Request(scope)


def _request_without_cookie() -> Request:
    return Request({'type': 'http', 'headers': []})


def test_send_sets_cookie_with_expected_attributes_for_str_message():
    response = Response()
    flash.send(response, 'hello')

    cookie = http.cookies.SimpleCookie()
    cookie.load(response.headers['set-cookie'])
    morsel = cookie['flash']

    assert _decode(morsel.value) == 'hello'
    assert morsel['httponly'] is True
    assert morsel['secure'] is True
    assert morsel['samesite'] == 'none'
    assert morsel['path'] == '/'
    assert morsel['max-age'] == '10'


def test_send_sets_cookie_for_dict_message():
    response = Response()
    flash.send(response, {'type': 'error', 'message': 'boom'})

    assert _decode(_cookie_value(response)) == {'type': 'error', 'message': 'boom'}


def test_read_returns_none_when_no_cookie_present():
    request = _request_without_cookie()
    response = Response()

    result = flash.read(request, response)

    assert result is None
    assert 'set-cookie' not in response.headers


def test_read_returns_value_and_deletes_cookie_when_present():
    send_response = Response()
    flash.send(send_response, {'type': 'success', 'message': 'ok'})

    request = _request_with_cookie_from(send_response)
    response = Response()

    result = flash.read(request, response)

    assert result == {'type': 'success', 'message': 'ok'}
    assert 'set-cookie' in response.headers
