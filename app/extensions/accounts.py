from app.utils import spec, RequestHandler, JsonErrors, CustomError


class Accounts(RequestHandler, require_token=False):
    @spec({
        "username": {"type": "string"},
        "password": {"type": "string"},
        "email": {"type": "string"}
    })
    async def post(self):
        try:
            account = await self.database.create_account(self.body["username"], self.body["email"], self.body["password"], self.tokens.create_id())
        except CustomError:
            return self.error(JsonErrors.invalid_form, email="Email is already registered.")

        self.write(account)
        self.flush()


def setup(app):
    return [(f"/api/v{app.version}/accounts", Accounts, app.args)]
