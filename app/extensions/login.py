
from app.utils import spec, RequestHandler, JsonErrors, CustomError

class Login(RequestHandler, require_token=False):
    @spec({
        "email": {"type": "string"},
        "password": {"type": "string"}
    })
    async def post(self):
        try:
            account = await self.database.get_account(self.body["email"], self.body["password"], with_settings=True)
        except CustomError:
            return self.error(JsonErrors.invalid_form, error="Email or password invalid.")

        token = self.tokens.create_token(account["id"])

        self.write({"token": token, "user_settings": account["user_settings"]})
        self.flush()

def setup(app):
    return [(f"/api/v{app.version}/login", Login, app.args)]

