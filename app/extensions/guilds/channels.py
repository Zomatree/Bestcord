from app.utils import spec, RequestHandler, JsonErrors, ChannelType, filter_channel_keys
import asyncpg

class Channels(RequestHandler):
    @spec({
        "name": {"type": "string", "minlength": 2, "maxlength": 100, "required": True},
        "type": {"type": "number", "allowed": [ChannelType.text, ChannelType.voice, ChannelType.category, ChannelType.news], "default": ChannelType.text},
        "topic": {"type": "string", "minlength": 0, "maxlength": 1024, "default": None, "nullable": True},
        "bitrate": {"type": "number", "dependencies": {"type": [0]}, "default": 0},
        "user_limit": {"type": "number", "default": 0},
        "rate_limit_per_user": {"type": "number", "min": 0, "max": 21600, "default": 0},
        "position": {"type": "number", "default": -1},
        "parent_id": {"type": "string", "default": None, "nullable": True},
        "nsfw": {"type": "boolean", "default": False},
        "permissions_overwrites": {"type": "list", "schema": {
            "type": "dict",
            "schema": {
                "id": {"type": "string", "required": True},
                "type": {"type": "number"},
                "allow": {"type": "string"},
                "deny": {"type": "string"}
            }
        }, "default": []}
    }, require_all=False)
    async def post(self, guild_id: str) -> None:
        id = self.tokens.create_id()
        name = self.body["name"]
        type = self.body["type"]
        topic = self.body["topic"] or None
        bitrate = self.body["bitrate"]
        user_limit = self.body["user_limit"]
        rate_limit_per_user = self.body["rate_limit_per_user"]
        # position = self.body["position"]  will be handled another time
        parent_id = self.body["parent_id"]
        nsfw = self.body["nsfw"]
        
        async with self.database.accqire() as conn:
            try:
                channel = await conn.fetchrow("insert into guild_channels values($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) returning *", name, id, type, topic, bitrate, user_limit, rate_limit_per_user, 0, parent_id, nsfw, guild_id)
            except asyncpg.exceptions.ForeignKeyViolationError:
                return self.error(JsonErrors.missing_access)

        channel = filter_channel_keys(dict(channel))  # type: ignore

        self.finish(channel)

        self.application.destinations["channel"][id] = self.application.destinations["guild"][guild_id]  # dont have permissions done yet so this is a botch fix

        self.application.dispatch_event("channel_create", channel, index_type="channel", index=id)

    async def get(self, guild_id: str):
        async with self.database.accqire() as conn:
            channels = await conn.fetch("select * from guild_channels where guild_id=$1", guild_id)
        
        channels = [filter_channel_keys(dict(channel)) for channel in channels]

        self.finish(channels)

class ChannelID(RequestHandler):
    async def delete(self, channel_id: str):
        async with self.database.accqire() as conn:
            channel = await conn.fetchrow("delete from guild_channels where id=$1 return *", channel_id)
        
        if not channel:
            return self.error(JsonErrors.missing_access, 403)

        self.set_status(204)
        self.flush()

        channel = filter_channel_keys(channel)

        self.application.dispatch_event("channel_delete", channel, index=channel_id, index_type="channel")
        del self.application.destinations["channel"][channel_id]

def setup(app):
    return [(f"/api/v{app.version}/guilds/(.+)/channels", Channels, app.args)]
