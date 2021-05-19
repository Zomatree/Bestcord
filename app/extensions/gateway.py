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
            "type": "integer",
            "allowed": [0,1,2,3,4,5,6,7,9,10,11]
        },
        "d": {
            "type": "dict",
            "allow_unknown": True
        }
    })

    identify = cerberus.Validator({
        "token": {"type": "string"},
        "intents": {"type": "integer"},
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

    def initialize(self, database: DB, tokens: Tokens):
        self.last_heartbeat_ack = datetime.datetime.utcnow()
        self.identity = None
        self.user_id = None
        self.s = 0
        self.queue = asyncio.Queue[tuple[str, dict[str, Any]]]()
        self.heartbeat_interval = self.application.config["gateway"]["heartbeat_interval"]
        
        return super().initialize(database, tokens)

    async def open(self):
        version = self.get_query_argument("v", default=None)
        if not version:
            return self.close(GatewayErrors.invalid_version, "Requested gateway version is no longer supported or invalid.")

        encoding = self.get_query_argument("encoding", default="json")
        if encoding != "json":
            return self.close(GatewayErrors.unknown, "Invalid encoding, only json is supported.")

        self.send_message(GatewayOps.hello, {"heartbeat_interval": self.heartbeat_interval})

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

            asyncio.create_task(self.dispatcher())

        if data["op"] == GatewayOps.heartbeat:
            self.last_heartbeat_ack = datetime.datetime.utcnow()

            # TODO: actually do heartbeating

    async def on_close(self):
        logging.info("Closing gateway connection with user id %s", self.user_id)

    async def dispatcher(self):
        while True:
            event_name, payload = await self.queue.get()
            self.send_message(GatewayOps.dispatch, payload, s=self.s, t=event_name)
            self.s += 1

def setup(app):
    return [(f"/api/v{app.version}/gateway/connect", Gateway, app.args)]
