
from app.utils import spec, RequestHandler, embed_spec, allowed_mentions_spec, JsonErrors
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

        message = {
            "id": id,
            "content": content,
            "embeds": embeds,
            "tts": tts,
        }

        if allowed_mentions is not None:
            message["allowed_mentions"] = allowed_mentions

        self.write(message)
        self.flush()

        self.application.dispatch_event("message_create", message, index=channel_id, index_type="channel")

def setup(app):
    return [(f"/api/v{app.version}/channels/(.+)/messages", Messages, app.args)]
