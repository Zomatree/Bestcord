from app.utils import spec, RequestHandler


class Test(RequestHandler):
    async def get(self):
        self.write({"id": self.user_id})
        self.flush()

def setup(app):
    return [(f"/api/v{app.version}/test", Test, app.args)]
