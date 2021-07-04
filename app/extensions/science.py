
from app.utils import spec, RequestHandler

class Science(RequestHandler):
    def get(self):
        pass

    def post(self):
        pass

def setup(app):
    return [(f"/api/v{app.version}/science", Science, app.args)]
