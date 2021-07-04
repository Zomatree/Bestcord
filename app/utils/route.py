from __future__ import annotations

from tornado.web import RequestHandler as BaseRequestHandler
from tornado.websocket import WebSocketHandler as BaseWebSocketHandler, WebSocketClosedError
from tornado.concurrent import Future
from tornado.httputil import HTTPServerRequest
import ujson
import math

from typing import Tuple, Optional, Callable, Awaitable, TYPE_CHECKING, Union, Dict, Any, TypeVar, overload

from .enums import HTTPErrors

if TYPE_CHECKING:
    from app.app import App
    from .database import DB
    from .token import Tokens
    T = TypeVar("T")

class RequestHandler(BaseRequestHandler):
    require_token: bool
    application: App
    request: HTTPServerRequest

    def __init_subclass__(cls, require_token: bool = True) -> None:
        cls.require_token = require_token

    def initialize(self, database: DB, tokens: Tokens):
        self.database = database
        self.tokens = tokens
        self.user_id: str = ""  # setting to an empty string instead of none makes my typing life easier

        self.body: dict[str, Any]

    async def prepare(self) -> None:
        if self.request.method == "OPTIONS":
            return

        if not self.require_token:
            return

        try:
            token: str = self.request.headers["Authorization"].replace("Bot ", "")
        except KeyError:
            return self.error(HTTPErrors.unauthorized, status_code=401)
            
        try:
            self.user_id = self.tokens.validate_token(token)
        except:
            return self.error(HTTPErrors.unauthorized, status_code=401)

        bucket = self.application.global_ratelimit.get_bucket(self.user_id)
        retry_after = bucket.update_ratelimit()

        if retry_after:
            self.set_status(429)
            return await self.finish({"message": "You are being rate limited.", "retry_after": retry_after, "global": False})

        self.set_header("X-RateLimit-Limit", 50)
        self.set_header("X-RateLimit-Remaining", bucket.get_tokens())
        self.set_header("X-RateLimit-Retry-After", math.ceil(bucket.get_retry_after()))
        self.set_header("X-RateLimit-Bucket", self.user_id)
        self.set_header("X-RateLimit-Reset", round(bucket._window + bucket.per))
        self.set_header("X-RateLimit-Global", True)

    def error(self, code: Tuple[int, str], status_code: int = 400, **kwargs: Any) -> None:
        return self.send_error(status_code, code=code[0], message=code[1], **kwargs)

    def write_error(self, status_code: int, **kwargs: Any):
        try:
            body = {"code": kwargs.pop("code"), "message": kwargs.pop("message")}
            if kwargs:
                body["errors"] = kwargs

        except KeyError:
            body = {"code": 0, "message": "Internal Server Error"}

        self.set_status(status_code)
        self.add_header("Content-Type", "application/json")
        self.finish(body)

    def write(self, body: Union[str, bytes, dict, list]) -> None:
        if isinstance(body, (dict, list)):
            self.set_header("Content-Type", "application/json")
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

    def options(self, *_):
        self.set_status(204)
        self.finish()

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "*")
        self.set_header("Access-Control-Allow-Methods", ", ".join(map(str.upper, self.SUPPORTED_METHODS)))

    @overload
    def get_query_argument(self, key: str, default: T) -> Union[str, T]:
        ...

    @overload
    def get_query_argument(self, key: str, default: None = None) -> Optional[str]:
        ...

    def get_query_argument(self, key: str, default: T = None) -> Union[str, T, None]:
        try:
            return self.request.query_arguments[key][0]
        except KeyError:
            return default

    # our custom .write takes a list as well so we need to modify .finish's signature to take it too

    def finish(self, chunk: Optional[Union[str, bytes, dict, list]] = None) -> Future[None]:
        return super().finish(chunk)  # type: ignore

class WebSocketHandler(BaseWebSocketHandler):
    application: App

    async def write_message(self, message: Union[bytes, str, Dict[str, Any]], binary: bool = False) -> None:
        if self.ws_connection is None or self.ws_connection.is_closing():
            raise WebSocketClosedError()
        if isinstance(message, dict):
            message = ujson.dumps(message)
        return await self.ws_connection.write_message(message, binary=binary)

    def initialize(self, database: DB, tokens: Tokens) -> None:
        self.database = database
        self.tokens = tokens
        self.user_id = None

        self.body: Optional[dict] = None

    async def send_message(self, op: int, d: Any, *, s: int = None, t: str = None) -> None:
        return await self.write_message({"op": op, "d": d, "s": s, "t": t})
