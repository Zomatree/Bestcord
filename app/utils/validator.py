from __future__ import annotations

import cerberus
import functools
import ujson
from typing import TypedDict, Any, Callable, Union, Literal

from .enums import JsonErrors
from .route import RequestHandler

class _OptionalSpec(TypedDict, total=False):
    allow_unknown: bool
    allowed: list[Any]
    allof: list[_OptionalSpec]
    anyof: list[_OptionalSpec]
    contains: Any
    dependencies: Union[str, list[str], dict[str, Union[list[Any], Any]]]
    empty: bool
    excludes: Union[str, list[str]]
    forbidden: list[str]
    items: list[_Spec]
    keyrules: _Spec
    meta: Any
    min: int
    max: int
    minlength: int
    maxlength: int
    noneof: list[_OptionalSpec]
    nullable: bool
    oneof: list[_OptionalSpec]
    regex: str
    require_all: bool
    required: bool
    valuerules: _Spec
    rename: str
    default: Any
    default_setter: Callable[["Spec"], Any]
    coerce: Callable[[Any], Any]

class Dict(_OptionalSpec, total=False):
    schema: Spec
    type: Literal["dict"]

class Generic(_OptionalSpec, total=False):
    schema: _Spec
    type: str

# dict takes a differant schema that regular 

_Spec = Union[Dict, Generic]
Spec = dict[str, _Spec]

# until cerberus 2.0 comes stable im using my own wrapper that the linter doesnt hate

class Validator:
    def __init__(self, spec, **kwargs):
        self._validator = cerberus.Validator(spec, **kwargs)
    
    def validate(self, body: dict[str, Any]) -> bool:
        return self._validator.validate(body)  # type: ignore
    
    def normalized(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._validator.normalized(body)  # type: ignore

    @property
    def errors(self) -> dict[str, Any]:
        return self._validator.errors  # type: ignore

def spec(spec: Spec, ignore_none_values: bool = False, allow_unknown: bool = False, require_all: bool = True, purge_unknown: bool = True, purge_readonly: bool = True) -> Callable:
    validator = Validator(spec, ignore_none_values=ignore_none_values, allow_unknown=allow_unknown, require_all=require_all, purge_unknown=purge_unknown, purge_readonly=purge_readonly)
    
    def inner(f) -> Callable:
        @functools.wraps(f)
        async def wrapper(self: RequestHandler, *args, **kwargs):
            raw_body = self.request.body
            if not raw_body:
                return self.error(JsonErrors.missing_key)

            body = ujson.loads(raw_body.decode())

            status = validator.validate(body)

            if not status:
                return self.error(JsonErrors.general, **validator.errors)
            
            body = validator.normalized(body)
            if not body:
                return self.error(JsonErrors.general, **validator.errors)

            self.body = body
            return await f(self, *args, **kwargs)
        return wrapper
    return inner
