
from app.utils import spec, RequestHandler, JsonErrors

class SpecificMembers(RequestHandler):
    async def get(self, guild_id: str, member_id: str):
        async with self.database.accqire() as conn:
            control = await conn.fetchval("select 1 from guild_members where guild_id=$1 and user_id=$2", guild_id, self.user_id)
            member = await conn.fetchrow("select joined_at, deaf, mute, pending, nick from guild_members where guild_id=$1 and user_id=$2", guild_id, member_id)

            if not control:
                return self.error(JsonErrors.missing_access, 403)
            if not member:
                return self.error(JsonErrors.unknown_user, 404)
 
            member = dict(member)
            member["user"] = await self.database.get_user(member_id)
            member["roles"] = await self.database.get_member_roles(member_id, guild_id, conn=conn)

        self.finish(member)

class Members(RequestHandler):
    async def get(self, guild_id: str):
        try:
            limit = int(self.get_query_argument("limit", 1))
            after = str(int(self.get_query_argument("after", 0)))
        except ValueError:
            return ...

        async with self.database.accqire() as conn:
            count = await conn.fetchval("select 1 from guild_members where guild_id=$1 and user_id=$2", guild_id, self.user_id)
            if count == 0:
                return self.error(JsonErrors.missing_access, 403)

            user_rows = await conn.fetch("select user_id, joined_at, deaf, mute, pending, nick from guild_members where guild_id=$1 and user_id > $2 order by user_id asc limit $3", guild_id, after, limit)
            
            members = []

            for row in user_rows:
                member = dict(row)
                user_id = member.pop("user_id")

                member["user"] = await self.database.get_user(user_id, conn=conn)
                member["roles"] = await self.database.get_member_roles(user_id, guild_id, conn=conn)
                members.append(member)
            
        self.finish(members)

def setup(app):
    return [
        (f"/api/v{app.version}/guilds/(.+)/members/(.+)", SpecificMembers, app.args),
        (f"/api/v{app.version}/guilds/(.+)/members", Members, app.args)
    ]

