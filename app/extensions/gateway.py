from app.utils import GatewayOps, GatewayErrors, WebSocketHandler, DB, Tokens, CustomError, Spec, Validator

from typing import Optional, Any
import datetime
import ujson
import asyncio
import logging

generic_spec: Spec = {
    "op": {
        "type": "number",
        "allowed": [0,1,2,3,4,5,6,7,9,10,11,12]
    },
    "d": {
        "allow_unknown": True,
        "nullable": True
    }
}
generic: Validator = Validator(generic_spec, allow_unknown=True)

identify_spec: Spec = {
    "token": {"type": "string"},
    "intents": {"type": "number"},
    "properties": {
        "type": "dict",
        "allow_unknown": True,
        "schema": {
            "$os": {"type": "string"},
            "$browser": {"type": "string"},
            "$device": {"type": "string"}
        }
    }
}

identify: Validator = Validator(identify_spec, allow_unknown=True)

member_chunk_spec: Spec = {
    "guild_id": {"type": "string"},
    "query": {"type": "string", "required": False, "excludes": "user_ids"},
    "limit": {"type": "string", "dependencies": "query"},
    "presences": {"type": "boolean", "required": False, "default": False},
    # "user_ids": {"type": "list", "schema": {"type": "string"}},
    "nonce": {"type": "string", "required": False}
}

member_chunk: Validator = Validator(member_chunk_spec, allow_unknown=True)

class Gateway(WebSocketHandler):
    last_heartbeat_ack: Optional[datetime.datetime]

    def initialize(self, database: DB, tokens: Tokens) -> None:
        self.heartbeat_event = asyncio.Event()
        self.last_heartbeat_ack = datetime.datetime.utcnow()
        self.identitied = False
        self.user_id = None
        self.s = 0
        self.guild_ids = []  # list of guild ids the user is in
        self.queue = asyncio.Queue[tuple[str, Any]]()
        self.heartbeat_interval = self.application.config["gateway"]["heartbeat_interval"]
        self.gateway_version = self.application.config["gateway"]["version"]
        self.started_at = datetime.datetime.utcnow()
        self.sleep_interval = (self.heartbeat_interval * 1.25) / 1000
        super().initialize(database, tokens)

    async def open(self):
        version = self.get_query_argument("v", default=None)
        if not version:
            return self.close(GatewayErrors.invalid_version, "Requested gateway version is no longer supported or invalid.")

        encoding = self.get_query_argument("encoding", default="json")
        if encoding != "json":
            return self.close(GatewayErrors.unknown, "Invalid encoding, only json is supported.")

        await self.send_message(GatewayOps.hello, {"heartbeat_interval": self.heartbeat_interval})

    async def on_message(self, message):
        try:
            data = ujson.loads(message)
        except:
            return self.close(GatewayErrors.decode_error, "Error decoding message.")
        
        logging.debug("Received payload: %s", data)

        status: bool = generic.validate(data)

        if not status:
            logging.debug(generic.errors)
            return self.close(GatewayErrors.decode_error, "Invalid payload")

        payload = data["d"]

        if data["op"] != GatewayOps.identify and self.identitied is False and (self.started_at + datetime.timedelta(seconds=self.sleep_interval) < datetime.datetime.utcnow()):
            return self.close(GatewayErrors.not_authed, "No identify message sent")

        elif data["op"] == GatewayOps.identify and self.identitied is not False:
            return self.close(GatewayErrors.already_authed, "Identify already sent")

        if data["op"] == GatewayOps.identify:
            status: bool = identify.validate(data["d"])
            if not status:
                return self.close(GatewayErrors.decode_error, "Invalid payload")

            token = payload["token"]

            try:
                self.user_id = self.tokens.validate_token(token)
            except CustomError:
                return self.close(GatewayErrors.auth_failed, "Invalid token")

            self.intents = payload["intents"]
            self.identitied = True
            self.application.gateway_connections[self.user_id] = self

            asyncio.create_task(self.dispatcher())
            asyncio.create_task(self.heartbeat_task())

            async with self.database.accqire() as conn:
                rows = await conn.fetch("select guild_id from guild_members where user_id=$1", self.user_id)
                guild_ids = [row["guild_id"] for row in rows]
            

                ready = {
                    "v": self.gateway_version,
                    "user": await self.database.get_user(self.user_id),
                    "guilds": [{"id": id, "unavailable": True} for id in guild_ids],
                    "session_id": 0,  # will do this eventually
                    "application": {
                        "id": self.user_id,
                        "flags": 0
                    }
                }

                self.push_event("ready", ready)

                for guild_id in guild_ids:
                    guild = await self.database.get_guild(guild_id, conn=conn, extra_info=True)
                    self.push_event("guild_create", guild)

        elif data["op"] == GatewayOps.heartbeat:
            self.last_heartbeat_ack = datetime.datetime.utcnow()
            self.heartbeat_event.set()
            await self.send_message(GatewayOps.heartbeat_ack, self.s)

        elif data["op"] == GatewayOps.request_guild_members:
            status: bool = member_chunk.validate(payload)
            if not status:
                return self.close(GatewayErrors.decode_error, "Invalid message shape")

            if (guild_id := payload["guild_id"]) not in self.guild_ids:
                return

            members = list(self.application.member_cache[guild_id].values())
            chunks = [members[i:i+1000] for i in range(0, len(members), 1000)]
            chunk_count = len(chunks)

            for i, chunk in enumerate(chunks):
                chunk = [member  | {"user": self.application.user_cache[member["id"]]} for member in chunk]

                chunk_payload = {
                    "guild_id": guild_id,
                    "members": chunk,
                    "chunk_index": i,
                    "chunk_count": chunk_count,
                    "presences": []
                }

                if (nonce := payload.get("nonce")):
                    payload["nonce"] = nonce

                self.push_event("guild_member_chunk", chunk_payload)

    async def heartbeat_task(self):
        delta = datetime.timedelta(seconds=self.sleep_interval)

        while True:
            await self.heartbeat_event.wait()
            await asyncio.sleep(self.sleep_interval)
            self.heartbeat_event.clear()

            behind = self.last_heartbeat_ack < datetime.datetime.utcnow() - delta
            
            if behind:
                self.close()

    def on_close(self):
        logging.info("Closing gateway connection with user id %s", self.user_id)
        if self.user_id is not None:
            del self.application.gateway_connections[self.user_id]

    async def dispatcher(self):
        while True:
            event_name, payload = await self.queue.get()
            await self.send_message(GatewayOps.dispatch, payload, s=self.s, t=event_name.upper())
            self.s += 1

    def push_event(self, event_name: str, payload: dict[str, Any]):
        self.queue.put_nowait((event_name, payload))

def setup(app):
    return [(f"/api/v{app.version}/gateway/connect", Gateway, app.args)]
