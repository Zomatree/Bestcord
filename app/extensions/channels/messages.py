
from app.utils import spec, RequestHandler, embed_spec, allowed_mentions_spec, JsonErrors, MessageTypes
from asyncpg.exceptions import ForeignKeyViolationError

class Messages(RequestHandler):
    @spec({
        "content": {"type": "string", "default": None, "minlength": 0, "maxlength": 2000, "nullable": True},
        "tts": {"type": "boolean", "default": False, "required": False},
        "embed": {"type": "dict", "schema": embed_spec, "required": False},
        "allowed_mentions": {"type": "dict", "schema": allowed_mentions_spec, "required": False, "default": None, "nullable": True}
    }, require_all=False)
    async def post(self, channel_id: str):
        content = self.body["content"]
        embed_passed = "embed" in self.body  # type: ignore
        tts = self.body["tts"]
        allowed_mentions = self.body["allowed_mentions"]

        if not content and not embed_passed:
            return self.error(JsonErrors.empty_message)

        embeds = []
        
        if embed_passed:
            embeds.append(self.body["embed"])
        
        id = self.tokens.create_id()

        async with self.database.accqire() as conn:
            try:
                await conn.execute("insert into messages(id, channel_id, content, tts, embeds, allowed_mentions) values ($1, $2, $3, $4, $5, $6)", id, channel_id, content, tts, embeds, allowed_mentions)
            except ForeignKeyViolationError:
                return self.error(JsonErrors.unknown_channel, status_code=404)

            guild_id = await conn.fetchval("select guild_id from guild_channels where id=$1", channel_id)

        message = {
            "id": id,
            "content": content,
            "embeds": embeds,
            "tts": tts,
            "channel_id": channel_id,
            "attachments": [],
            "edited_timestamp": None,
            "type": MessageTypes.default,
            "pinned": False,
            "mention_everyone": False,
            "mentions": []
        }

        if allowed_mentions is not None:
            message["allowed_mentions"] = allowed_mentions

        self.write(message)
        self.flush()

        message["author"] = self.application.user_cache[self.user_id]
        message["member"] = self.application.member_cache[guild_id][self.user_id]  # type: ignore

        print(message)

        self.application.dispatch_event("message_create", message, index=channel_id, index_type="channel")

    async def get(self, channel_id: str):
        limit = self.get_query_argument("limit", "100")

        async with self.database.accqire() as conn:
            messages = await conn.fetch("select * from messages where channel_id=$1 order by id desc limit $2", channel_id, limit)
        
        self.write(messages)
        self.flush()

def setup(app):
    return [(f"/api/v{app.version}/channels/(.+)/messages", Messages, app.args)]
