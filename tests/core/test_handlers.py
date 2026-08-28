import base64
import http.cookies
import json

from fastapi import HTTPException

from app.core.handlers import generic_exception_handler, http_exception_handler
from app.schemas.internal import AppMessage


def _flash_value(response):
    cookie = http.cookies.SimpleCookie()
    cookie.load(response.headers['set-cookie'])
    return json.loads(base64.urlsafe_b64decode(cookie['flash'].value.encode()))


async def test_http_exception_handler_returns_json_body_and_status():
    exc = HTTPException(404, detail='No encontrado')
    response = await http_exception_handler(None, exc)
    assert response.status_code == 404
    assert json.loads(response.body) == {'detail': 'No encontrado'}


async def test_http_exception_handler_forwards_custom_headers():
    exc = HTTPException(401, detail='msg', headers={'X-Test': 'yes'})
    response = await http_exception_handler(None, exc)
    assert response.headers.get('x-test') == 'yes'


async def test_http_exception_handler_sets_flash_cookie():
    exc = HTTPException(403, detail='Prohibido')
    response = await http_exception_handler(None, exc)
    assert _flash_value(response) == AppMessage.error('Prohibido').dict()


async def test_generic_exception_handler_returns_fixed_500_body_without_leaking_message():
    response = await generic_exception_handler(None, Exception('sensitive internal detail'))
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body == {'detail': 'Hubo un error inesperado.'}
    assert 'sensitive internal detail' not in response.body.decode()


async def test_generic_exception_handler_sets_flash_cookie():
    response = await generic_exception_handler(None, Exception('boom'))
    assert _flash_value(response) == AppMessage.error('Hubo un error inesperado.').dict()
