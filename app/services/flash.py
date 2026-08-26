import json
from fastapi import Request, Response


FLASH_KEY = 'flash'

_flash_args = {
    'key': FLASH_KEY,
    'httponly': True,
    'secure': True,
    'samesite': 'none',
    'path': '/'
}

type FlashCookie = str | dict

def send[T: FlashCookie](response: Response, message: T):
    response.set_cookie(
        value=json.dumps(message),
        **_flash_args,
        max_age=10
    )

def read[T: FlashCookie](request: Request, response: Response) -> T | None:
    raw = request.cookies.get(FLASH_KEY)
    if raw is None:
        return None
    response.delete_cookie(**_flash_args)
    return json.loads(raw)
