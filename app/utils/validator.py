import cerberus
import functools
import ujson

from .errors import JsonErrors

from .route import RequestHandler

def spec(spec, ignore_none_values=False, allow_unknown=False, require_all=True, purge_unknown=True, purge_readonly=True):
    validator = cerberus.Validator(spec, ignore_none_values=ignore_none_values, allow_unknown=allow_unknown, require_all=require_all, purge_unknown=purge_unknown, purge_readonly=purge_readonly)
    def inner(f):
        @functools.wraps(f)
        async def wrapper(self: RequestHandler):
            raw_body = self.request.body
            if not raw_body:
                return self.error(JsonErrors.missing_key)

            body = ujson.loads(raw_body.decode())

            status: bool = validator.validate(body)  # type: ignore

            if not status:
                return self.error(JsonErrors.general, **validator.errors)  # type: ignore
            
            self.body = body
            return await f(self)
        return wrapper
    return inner
