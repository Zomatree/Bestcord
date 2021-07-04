from app.utils import spec, RequestHandler, ratelimit

class Test(RequestHandler):
    @ratelimit(2, 5)
    async def get(self):
        self.finish({"id": self.user_id})

def setup(app):
    return [(f"/api/v{app.version}/test", Test, app.args)]
