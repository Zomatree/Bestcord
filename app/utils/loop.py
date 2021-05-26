import uvloop
from tornado.platform.asyncio import BaseAsyncIOLoop

from typing import Any

class TornadoUvloop(BaseAsyncIOLoop):
    def initialize(self, **kwargs: Any) -> None:
        loop = uvloop.new_event_loop()
        try:
            super().initialize(loop, close_loop=True, **kwargs)
        except Exception:
            loop.close()
            raise
