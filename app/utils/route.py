from __future__ import annotations

from tornado.web import RequestHandler as BaseRequestHandler
from tornado.websocket import WebSocketHandler as BaseWebSocketHandler, WebSocketClosedError
import ujson

from typing import Tuple, Optional, Callable, Awaitable, TYPE_CHECKING, Union, Dict, Any

from .errors import HTTPErrors

if TYPE_CHECKING:
    from app.app import App
    from .database import DB
    from .token import Tokens

class RequestHandler(BaseRequestHandler):
    require_token: bool
    application: App

    def __init_subclass__(cls, require_token=True) -> None:
        cls.require_token = require_token

    def initialize(self, database: DB, tokens: Tokens):
        self.database = database
        self.tokens = tokens
        self.user_id = None

        self.body: Optional[dict] = None

    async def prepare(self):
        if not self.require_token:
            return 

        try:
            token: str = self.request.headers["Authorization"]
        except KeyError:
            return self.error(HTTPErrors.unauthorized, status_code=401)
            
        try:
            self.user_id = self.tokens.validate_token(token)
        except:
            return self.error(HTTPErrors.unauthorized, status_code=401)

    def error(self, code: Tuple[int, str], status_code=400, **kwargs) -> None:
        return self.send_error(status_code, code=code[0], message=code[1], **kwargs)

    def write_error(self, status_code: int, **kwargs):
        body = {"code": kwargs.pop("code"), "message": kwargs.pop("message")}
        
        if kwargs:
            body["errors"] = kwargs
        
        self.set_status(status_code)
        self.add_header("Content-Type", "application/json")
        self.write(ujson.dumps(body))
        self.finish()

    def write(self, body):
        if isinstance(body, dict):
            body = ujson.dumps(body)
        
        return super().write(body)

    def _unimplemented_method(self, *args: str, **kwargs: str) -> None:
        self.error(HTTPErrors.invalid_method, status_code=405)

    head = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    get = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    post = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    delete = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    patch = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    put = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]
    options = _unimplemented_method  # type: Callable[..., Optional[Awaitable[None]]]


class WebSocketHandler(BaseWebSocketHandler):
    application: App

    def write_message(self, message: Union[bytes, str, Dict[str, Any]], binary: bool = False):
        if self.ws_connection is None or self.ws_connection.is_closing():
            raise WebSocketClosedError()
        if isinstance(message, dict):
            message = ujson.dumps(message)
        return self.ws_connection.write_message(message, binary=binary)

    def initialize(self, database: DB, tokens: Tokens):
        self.database = database
        self.tokens = tokens
        self.user_id = None

        self.body: Optional[dict] = None

    def send_message(self, op: int, d: Dict[str, Any], *, s: int = None, t: str = None):
        return self.write_message({"op": op, "d": d, "s": s, "t": t})
