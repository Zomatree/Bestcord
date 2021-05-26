from __future__ import annotations

from tornado.web import Application, StaticFileHandler, RedirectHandler
import importlib
import asyncio
from typing import Any, Protocol, runtime_checkable, Literal, get_args

from .utils import DB, TornadoUvloop, Tokens
from .extensions.gateway import Gateway
@runtime_checkable
class ExtensionProtocol(Protocol):
    @staticmethod
    def setup(app: App) -> list[Any]:
        raise NotImplementedError

destination_keys = Literal["guild", "channel"]

class App(Application):
    def __init__(self, database: DB, config: dict[str, Any]):
        self.database = database
        self.config = config
        self.version = config["version"]

        token_config: dict[str, Any] = config["tokens"]
        self.tokens = Tokens(token_config["epoch"], token_config["worker_id"], token_config["process_id"], token_config["secret_key"])

        self.args = {"database": self.database, "tokens": self.tokens}
        
        self.gateway_connections: dict[str, Gateway] = {}  # id -> gateway
        self.destinations: dict[destination_keys, dict[str, list[str]]] = {}  # type -> (id -> userid[])

        for key in get_args(destination_keys):
            self.destinations[key] = {}

        files: list[str] = config["extensions"]
        routes = []

        for file in files:
            module_path = f"app.extensions.{file}"
            module = importlib.import_module(module_path)
            if not isinstance(module, ExtensionProtocol):
                raise Exception(f"'{module_path}' is missing a setup function")
            
            module_routes = module.setup(self)
            
            routes.extend(module_routes)

        routes.append(("/", RedirectHandler, {"url": "/index.html"}))
        routes.append(("/(.+)", StaticFileHandler, {"path": "./app/static"}))

        for route in routes:
            print(f"Adding {route[0]}")

        super().__init__(routes)

    @classmethod
    def run(cls, config: dict[str, Any]):
        TornadoUvloop.current().make_current()
        loop = asyncio.get_event_loop()
        db = loop.run_until_complete(DB.from_args(config["database"]))
        server = cls(db, config)
        loop.run_until_complete(server.fill_destinations())
        server.listen(config["app"]["port"], config["app"]["address"])
        print(f"running at http://{config['app']['address']}:{config['app']['port']}")
        TornadoUvloop.current().start()

    def dispatch_event(self, event_name: str, payload: dict[str, Any], *, index: str, index_type: destination_keys):
        users = self.destinations[index_type][index]
        for id in users:
            self.gateway_connections[id].push_event(event_name, payload)

    async def fill_destinations(self):
        async with self.database.accqire() as conn:
            guilds = await conn.fetch("select guilds.id, guild_members.user_id from guilds left join guild_members on guilds.id = guild_members.guild_id")
            channels = await conn.fetch("select id, guild_id from guild_channels")

        for guild in guilds:
            self.destinations["guild"].setdefault(guild["id"], []).append(guild["user_id"])

        for channel in channels:
            self.destinations["channel"][channel["id"]] = self.destinations["guild"][channel["guild_id"]]  # ill switch this to permissions when i implement them, until then its the same as guilds
