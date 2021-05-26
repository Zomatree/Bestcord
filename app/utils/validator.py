from __future__ import annotations

import cerberus
import functools
import ujson
from typing import TypedDict, Any, Callable, Union, Literal

from .errors import JsonErrors
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

class DictSchema(_OptionalSpec, total=False):
    schema: Spec

class Dict(DictSchema):
    type: Literal["dict"]

class GenericSchema(_OptionalSpec, total=False):
    schema: _Spec

class Generic(GenericSchema):
    type: str

# dict takes a differant schema that regular 

_Spec = Union[Dict, Generic]
Spec = dict[str, _Spec]


def spec(spec: Spec, ignore_none_values: bool = False, allow_unknown: bool = False, require_all: bool = True, purge_unknown: bool = True, purge_readonly: bool = True) -> Callable:
    validator = cerberus.Validator(spec, ignore_none_values=ignore_none_values, allow_unknown=allow_unknown, require_all=require_all, purge_unknown=purge_unknown, purge_readonly=purge_readonly)
    
    def inner(f) -> Callable:
        @functools.wraps(f)
        async def wrapper(self: RequestHandler, *args, **kwargs):
            raw_body = self.request.body
            if not raw_body:
                return self.error(JsonErrors.missing_key)

            body = ujson.loads(raw_body.decode())

            status: bool = validator.validate(body)  # type: ignore

            if not status:
                return self.error(JsonErrors.general, **validator.errors)  # type: ignore
            
            body = validator.normalized(body)  # type: ignore

            self.body = body
            return await f(self, *args, **kwargs)
        return wrapper
    return inner
