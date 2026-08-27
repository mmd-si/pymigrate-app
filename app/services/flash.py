import base64
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
    # base64-encode so the cookie value is plain ASCII: raw JSON contains
    # commas/quotes, which different HTTP cookie-jar implementations
    # quote/escape inconsistently and can fail to round-trip.
    encoded = base64.urlsafe_b64encode(json.dumps(message).encode()).decode()
    response.set_cookie(
        value=encoded,
        **_flash_args,
        max_age=10
    )

def read[T: FlashCookie](request: Request, response: Response) -> T | None:
    raw = request.cookies.get(FLASH_KEY)
    if raw is None:
        return None
    response.delete_cookie(**_flash_args)
    return json.loads(base64.urlsafe_b64decode(raw.encode()))
