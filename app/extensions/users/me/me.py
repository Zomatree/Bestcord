
from app.utils import spec, RequestHandler

class Me(RequestHandler):
    async def get(self):
        async with self.database.accqire() as conn:
            row = await conn.fetchrow("select username, discriminator, id from users where id=$1", self.user_id)

        user = dict(row)  # type: ignore

        self.finish(user)

def setup(app):
    return [(f"/api/v{app.version}/users/@me", Me, app.args)]

