
from app.utils import spec, RequestHandler, HTTPErrors
import datetime

class Invites(RequestHandler):
    @spec({
        "max_age": {"type": "number", "default": 86400, "max": 604800, "min": 0, "required": False},
        "max_uses": {"type": "number", "min": 0, "max": 100, "default": 0, "required": False},
        "unique": {"type": "boolean", "default": False, "required": False},
        "temporary": {"type": "boolean", "default": False, "required": False},
    })
    async def post(self, channel_id: str):
        code = self.tokens.generate_invite_code()  # the likelyhood of 2 having the same code is very low so im just going to pretend it wont happen
        created_at = datetime.datetime.utcnow()

        if (max_age := self.body["max_age"]):
            expires_at = (created_at + datetime.timedelta(seconds=max_age)).isoformat()
        else:
            expires_at = None

        async with self.database.accqire() as conn:
            try:
                guild_id = await self.database.get_guild_id_from_channel_id(channel_id)
            except:
                return self.error(HTTPErrors.unauthorized, error=401)

            guild = await self.database.get_guild(guild_id, partial=True)

            await conn.execute("insert into guild_invites(code, channel_id, max_uses, guild_id, expires_at, inviter_id, max_age, temporary, created_at) values($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                               code, channel_id, self.body["max_uses"], guild_id, expires_at, self.user_id, max_age, self.body["temporary"], created_at.isoformat())

            channel = await self.database.get_channel(channel_id, conn=conn, partial=True)
            inviter = await self.database.get_user(self.user_id)
        
        payload = {
            "code": code,
            "guild": guild,
            "channel": channel,
            "inviter": inviter,
            "expires_at": expires_at
        }

        self.finish(payload)

        payload["guild_id"] = payload.pop("guild")["id"]
        payload["channel_id"] = payload.pop("channel")["id"]

        self.application.dispatch_event("invite_create", payload, index=channel_id, index_type="channel")

def setup(app):
    return [(f"/api/v{app.version}/channels/(.+)/invites", Invites, app.args)]
