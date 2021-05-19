
from app.utils import spec, RequestHandler

class GetGateway(RequestHandler, require_token=False):
    async def get(self):
        self.write({"url": f"{self.application.config['app']['public_url']}/api/v{self.application.version}/gateway/connect"})
    
class GetBotGateway(RequestHandler):
    async def get(self):
        self.write({
            "url": f"{self.application.config['app']['public_url']}/api/v{self.application.version}/gateway/connect",
            "shards": 1,  # haha sharding go brrr
            "session_start_limit": {
                "total": 1000,
                "remaining": 1000,
                "reset_after": 0,
                "max_concurrency": 1
            }
        })
def setup(app):
    return [
        (f"/api/v{app.version}/gateway", GetGateway, app.args),
        (f"/api/v{app.version}/gateway/bot", GetBotGateway, app.args),
    ]
