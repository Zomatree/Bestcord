
from app.utils import spec, RequestHandler, JsonErrors, now


class Guild(RequestHandler):
    @spec({
        "name": {"type": "string", "maxlength": 100, "minlength": 2},
        "region": {"type": "string", "required": False},
        "icon": {"type": "binary", "required": False},
        "verification_level": {"type": "number", "allowed": [0, 1, 2, 3, 4], "required": False, "default": 0},
        "default_message_notifications": {"type": "number", "allowed": [0, 1], "required": False, "default": 0},
        "explicit_content_filter": {"type": "number", "allowed": [0, 1, 2], "default": 0},
        "roles": {
            "type": "list",
            "default": [],
            "required": False,
            "schema": {"type": "dict", "schema": {
                "id": {"type": "string", "default": "0"},
                "name": {"type": "string"},
                "color": {"type": "number", "default": 0xFFFFFF},
                "hoist": {"type": "boolean", "default": False},
                "position": {"type": "number", "default": -1},
                "permissions": {"type": "string", "default": "0"},
                "managed": {"type": "boolean", "default": False},
                "mentionable": {"type": "boolean", "default": False},
            }}
        },
        "channels": {
            "type": "list",
            "default": [],
            "required": False,
            "schema": {"type": "dict", "schema": {
                "name": {"type": "string"},
                "type": {"type": "number", "allowed": []},
                "id": {"type": "string", "default": None},
                "parent_id": {"type": "string", "default": None}
            }}
        }
    })
    async def post(self) -> None:
        name = self.body["name"]
        roles = self.body["roles"]
        channels = self.body["channels"]
        verification_level = self.body["verification_level"]
        default_message_notifications = self.body["default_message_notifications"]
        explicit_content_filter = self.body["explicit_content_filter"]

        guild_id = self.tokens.create_id()
        now = now()

        async with self.database.accqire() as conn:
            guild = await conn.fetchrow("insert into guilds(name, id, owner_id, verification_level, default_message_notifications, explicit_content_filter) values($1, $2, $3, $4, $5, $6) returning *",
                                        name, guild_id, self.user_id, verification_level, default_message_notifications, explicit_content_filter)

            member = await conn.fetch("insert into guild_members(user_id, guild_id, joined_at) values ($1, $2, $3) returning *", self.user_id, guild_id, now)

        # TODO: do roles and channels

        guild = dict(guild)  # type: ignore
        guild["roles"] = []
        guild["emojis"] = []

        self.write(dict(guild))  # type: ignore
        self.flush()

        guild["members"] = [member]
        guild["voice_states"] = []
        guild["channels"] = []
        guild["threads"] = []
        guild["presences"] = []
        guild["member_count"] = 1

        member = {
            "id": self.user_id,
            "nick": None,
            "mute": False,
            "deaf": False,
            "joined_at": now
        }

        self.application.member_cache[guild_id][self.user_id] = member
        self.application.destinations["guild"][guild_id] = [self.user_id]
        self.application.dispatch_event("guild_create", guild, index=guild_id, index_type="guild")

class GuildID(RequestHandler):
    async def get(self, guild_id: str) -> None:
        async with self.database.accqire() as conn:
            guild = await conn.fetchrow("select * from guilds where id=$1 and exists (select 1 from guild_members where guild_id=$1 and user_id=$2)", guild_id, self.user_id)
        
            if guild is None:
                return self.error(JsonErrors.missing_key, 403)

        self.write(dict(guild))
        self.flush()

    @spec({
        "name": {"type": "string", "maxlength": 100, "minlength": 2},
        "icon": {"type": "binary", "nullable": True},
        "verification_level": {"type": "number", "allowed": [0, 1, 2, 3, 4]},
        "default_message_notifications": {"type": "number", "allowed": [0, 1]},
        "afk_channel_id": {"type": "string", "nullable": True},
        "afk_timeout": {"type": "string"},
        "owner_id": {"type": "string"},
        "description": {"type": "string", "nullable": True}
    }, require_all=False)
    async def patch(self, guild_id: str) -> None:
        async with self.database.accqire() as conn:
            new_guild = await conn.fetchrow("""update guilds set
                name=coalesce($2, name),
                icon=coalesce($3, icon),
                verification_level=coalesce($4, verification_level),
                default_message_notifications=coalesce($5, default_message_notifications),
                afk_channel_id=coalesce($6, afk_channel_id),
                afk_timeout=coalesce($7, afk_timeout),
                owner_id=coalesce($8, owner_id),
                description=coalesce($9, description) returning *
            """, guild_id, self.body.values())  # im just going to hope the order is always going to be the same, each item does have a default so in theory this shouldnt break

        new_guild = dict(new_guild)  # type: ignore

        self.write(new_guild)
        self.application.dispatch_event("guild_update", new_guild, index=guild_id, index_type="guild")

    async def delete(self, guild_id: str) -> None:
        async with self.database.accqire() as conn:
            response = await conn.execute("delete from guilds where id=$1 and owner_id=$2", guild_id, self.user_id)
        
        if response == "0":
            return self.error(JsonErrors.missing_access, 403)

        self.set_status(204)
        self.flush()

        self.application.dispatch_event("guild_delete", {"id": guild_id, "unavailable": False}, index=guild_id, index_type="guild")
        del self.application.destinations["guild"][guild_id]

def setup(app):
    return [
        (f"/api/v{app.version}/guilds", Guild, app.args),
        (f"/api/v{app.version}/guilds/(.+)", GuildID, app.args),
    ]
