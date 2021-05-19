from __future__ import annotations

from tornado.web import Application, StaticFileHandler, RedirectHandler
import importlib
import asyncio

from .utils import DB, TornadoUvloop, Tokens, RequestHandler
from typing import List, Tuple, Any, TYPE_CHECKING

class App(Application):
    def __init__(self, database: DB, config):
        self.database = database
        self.config = config

        self.version = config["version"]

        token_config = config["tokens"]
        self.tokens = Tokens(token_config["epoch"], token_config["worker_id"], token_config["process_id"], token_config["secret_key"])

        self.args = {"database": self.database, "tokens": self.tokens}

        files = config["extensions"]
        routes = []
        for file in files:
            module = importlib.import_module(f"app.extensions.{file}")
            module_routes = module.setup(self)  # type: ignore
            
            routes.extend(module_routes)

        routes.append(("/", RedirectHandler, {"url": "/index.html"}))
        routes.append(("/(.*)", StaticFileHandler, {"path": "./app/static"}))

        super().__init__(routes)

    @classmethod
    def run(cls, config):
        TornadoUvloop.current().make_current()
        loop = asyncio.get_event_loop()
        db = loop.run_until_complete(DB.from_args(config["database"]))
        server = cls(db, config)
        server.listen(config["app"]["port"], config["app"]["address"])
        print(f"running at http://{config['app']['address']}:{config['app']['port']}")
        TornadoUvloop.current().start()

