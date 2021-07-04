"""
The MIT License (MIT)
Copyright (c) 2015-present Rapptz
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

This file originates from https://github.com/Rapptz/discord.py/blob/master/discord/ext/commands/cooldowns.pyhttps://github.com/Rapptz/discord.py/blob/99fc9505107183faa59aad9e7753f293eba88836/discord/ext/commands/cooldowns.py
"""

from __future__ import annotations

import functools
import time
import math
from typing import Awaitable, Callable, Optional, TypeVar, Union
from typing_extensions import Concatenate, ParamSpec

from .route import RequestHandler

class Ratelimit:
    __slots__ = ("rate", "per", "_window", "_tokens", "_last")

    def __init__(self, rate: int, per: int):
        self.rate = int(rate)
        self.per = int(per)
        self._window = 0.0
        self._tokens: int = self.rate
        self._last = 0.0

    def get_tokens(self, current: Optional[float] = None) -> int:
        if not current:
            current = time.time()

        tokens = self._tokens

        if current > self._window + self.per:
            tokens = self.rate
        return tokens

    def get_retry_after(self, current: Optional[float] = None) -> float:
        current = current or time.time()
        tokens = self.get_tokens(current)

        if tokens == 0:
            return self.per - (current - self._window)

        return 0.0

    def update_ratelimit(self, current: Optional[float] = None) -> Optional[float]:
        current = current or time.time()
        self._last = current

        self._tokens = self.get_tokens(current)

        if self._tokens == self.rate:
            self._window = current

        if self._tokens == 0:
            return self.per - (current - self._window)

        self._tokens -= 1

        if self._tokens == 0:
            self._window = current

    def reset(self) -> None:
        self._tokens = self.rate
        self._last = 0.0

    def copy(self) -> Ratelimit:
        return Ratelimit(self.rate, self.per)

    def __repr__(self) -> str:
        return f"<Ratelimit {self.rate=} {self.per=} {self._window=} {self._tokens=}>"

class RatelimitMapping:
    __slots__ = ("_cache", "_cooldown")

    def __init__(self, original: Ratelimit):
        self._cache: dict[str, Ratelimit] = {}
        self._cooldown = original

    def copy(self) -> RatelimitMapping:
        ret = self.__class__(self._cooldown)
        ret._cache = self._cache.copy()
        return ret

    @property
    def valid(self) -> bool:
        return self._cooldown is not None

    @classmethod
    def from_ratelimit(cls, rate: int, per: int) -> RatelimitMapping:
        return cls(Ratelimit(rate, per))

    def _verify_cache_integrity(self, current: Optional[float] = None):
        current = current or time.time()
        dead_keys = [k for k, v in self._cache.items() if current > v._last + v.per]
        for k in dead_keys:
            del self._cache[k]

    def create_bucket(self):
        return self._cooldown.copy()

    def get_bucket(self, user_id: str, current: Optional[float] = None) -> Ratelimit:
        self._verify_cache_integrity(current)
        if user_id not in self._cache:
            bucket = self._cooldown.copy()
            self._cache[user_id] = bucket
        else:
            bucket = self._cache[user_id]

        return bucket

    def update_ratelimit(self, user_id: str, current: Optional[float] = None) -> Optional[float]:
        bucket = self.get_bucket(user_id, current)
        return bucket.update_ratelimit(current)

P = ParamSpec("P")
R = TypeVar("R")

def ratelimit(rate: int, per: int):
    mapping = RatelimitMapping.from_ratelimit(rate, per)

    def inner(func: Callable[Concatenate[RequestHandler, P], Awaitable[R]]) -> Callable[Concatenate[RequestHandler, P], Awaitable[Union[R, None]]]:
        @functools.wraps(func)
        async def wrapper(self: RequestHandler, *args: P.args, **kwargs: P.kwargs) -> Union[R, None]:
            bucket = mapping.get_bucket(self.user_id)
            retry_after = bucket.update_ratelimit()

            if retry_after:
                self.set_status(429)
                self.finish({"message": "You are being rate limited.", "retry_after": retry_after, "global": False})
                return

            self.set_header("X-RateLimit-Limit", rate)
            self.set_header("X-RateLimit-Remaining", bucket.get_tokens())
            self.set_header("X-RateLimit-Retry-After", math.ceil(bucket.get_retry_after()))
            self.set_header("X-RateLimit-Bucket", self.user_id)
            self.set_header("X-RateLimit-Reset", round(bucket._window + bucket.per))

            return await func(self, *args, **kwargs)

        return wrapper
    return inner
