from app.utils import GatewayOps, GatewayErrors, WebSocketHandler, DB, Tokens, CustomError

from typing import Optional, Any
import datetime
import ujson
import cerberus
import asyncio
import logging

class Specs:
    generic = cerberus.Validator({
        "op": {
            "type": "number",
            "allowed": [0,1,2,3,4,5,6,7,9,10,11]
        },
        "d": {
            "type": "dict",
            "allow_unknown": True
        }
    })

    identify = cerberus.Validator({
        "token": {"type": "string"},
        "intents": {"type": "number"},
        "properties": {
            "type": "dict",
            "schema": {
                "$os": {"type": "string"},
                "$browser": {"type": "string"},
                "$device": {"type": "string"}
            }
        }
    })

class Gateway(WebSocketHandler):
    last_heartbeat_ack: Optional[datetime.datetime]

    def initialize(self, database: DB, tokens: Tokens) -> None:
        self.last_heartbeat_ack = datetime.datetime.utcnow()
        self.identity = None
        self.user_id = None
        self.s = 0
        self.queue = asyncio.Queue[tuple[str, dict[str, Any]]]()
        self.heartbeat_interval = self.application.config["gateway"]["heartbeat_interval"]
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
        
        status: bool = Specs.generic.validate(data)  # type: ignore
        if not status:
            return self.close(GatewayErrors.decode_error, "Invalid message shape")
    
        if data["op"] != GatewayOps.identify and self.identity is None:
            return self.close(GatewayErrors.not_authed, "No identify message sent")

        if data["op"] == GatewayOps.identify and self.identity is not None:
            return self.close(GatewayErrors.already_authed, "Identify already sent")

        if data["op"] == GatewayOps.identify:
            status: bool = Specs.identify.validate(data["d"])  # type: ignore
            if not status:
                return self.close(GatewayErrors.decode_error, "Invalid message shape")

            payload = data["d"]
            token = payload["token"]

            try:
                self.user_id = self.tokens.validate_token(token)
            except CustomError:
                return self.close(GatewayErrors.auth_failed, "Invalid token")

            self.intents = payload["intents"]

            self.application.gateway_connections[self.user_id] = self

            asyncio.create_task(self.dispatcher())
            asyncio.create_task(self.heartbeat_task())

        if data["op"] == GatewayOps.heartbeat:
            self.last_heartbeat_ack = datetime.datetime.utcnow()

    async def heartbeat_task(self):
        sleep_interval = (self.heartbeat_interval * 1.25) / 1000
        delta = datetime.timedelta(seconds=sleep_interval)

        while True:
            asyncio.sleep(sleep_interval)
            if self.last_heartbeat_ack < datetime.datetime.utcnow() - delta:
                self.close()

    def on_close(self):
        logging.info("Closing gateway connection with user id %s", self.user_id)
        if self.user_id is not None:
            del self.application.gateway_connections[self.user_id]

    async def dispatcher(self):
        while True:
            event_name, payload = await self.queue.get()
            await self.send_message(GatewayOps.dispatch, payload, s=self.s, t=event_name)
            self.s += 1

    def push_event(self, event_name: str, payload: dict[str, Any]):
        self.queue.put_nowait((event_name, payload))

def setup(app):
    return [(f"/api/v{app.version}/gateway/connect", Gateway, app.args)]
