
from app.utils import spec, RequestHandler, HTTPErrors
import datetime

"""
{'code': 'KhPan9PVbp', 'guild': {
    'id': '471354723727966208',
    'name': 'testing',
    'splash': None,
    'banner': None,
    'description': None,
    'icon': 'aa27cc192a0a2a6a452fbd9e34538b25',
    'features': ['COMMUNITY', 'NEWS', 'WELCOME_SCREEN_ENABLED'],
    'verification_level': 2,
    'vanity_url_code': None,
    'nsfw': False,
    'nsfw_level': 0},
'channel': {'id': '576592045330792458', 'name': 'general', 'type': 0},
'inviter': {'id': '380423502810972162', 'username': 'Champions', 'avatar': 'ac62e0954c81b64da21ddf9278296423', 'discriminator': '1090', 'public_flags': 0, 'bot': True},
'approximate_member_count': 6,
'approximate_presence_count': 4,
'expires_at': None.
'expired_at': None}
"""

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
            expires_at = created_at + datetime.timedelta(seconds=max_age)
        else:
            expires_at = None

        async with self.database.accqire() as conn:
            try:
                guild_id = await self.database.get_guild_id_from_channel_id(channel_id)
            except:
                return self.error(HTTPErrors.unauthorized, error=401)

            guild = await self.database.get_guild(guild_id, partial=True)

            await conn.execute("insert into guild_invites(code, channel_id, max_uses, guild_id, expires_at, inviter_id, max_age, temporary, created_at) values($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                               code, channel_id, self.body["max_uses"], guild_id, expires_at.isoformat(), self.user_id, max_age, self.body["temporary"], created_at.isoformat())

            channel = await self.database.get_channel(channel_id, conn=conn, partial=True)
            inviter = await self.database.get_user(self.user_id)
        
        payload = {
            "code": code,
            "guild": guild,
            "channel": channel,
            "inviter": inviter,
            "expires_at": expires_at.isoformat()
        }

        self.finish(payload)

        payload["guild_id"] = payload.pop("guild")["id"]
        payload["channel_id"] = payload.pop("channel")["id"]

        self.application.dispatch_event("invite_create", payload, index=channel_id, index_type="channel")


def setup(app):
    return [(f"/api/v{app.version}/channels/(.+)/invites", Invites, app.args)]
