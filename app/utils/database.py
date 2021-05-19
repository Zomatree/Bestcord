from __future__ import annotations

import asyncpg
import contextlib
import argon2

from .errors import CustomError

all_discrims = set(str(d).rjust(4, "0") for d in range(1, 1000))

class DB:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.hasher = argon2.PasswordHasher()

    @classmethod
    async def from_args(cls, args):
        pool = await asyncpg.create_pool(**args)
        assert pool
        return cls(pool)

    @contextlib.asynccontextmanager
    async def accqire(self):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                conn: asyncpg.Connection
                yield conn

    async def create_account(self, username, email, password, id):
        async with self.accqire() as conn:
            hashed = self.hasher.hash(password)

            users = await conn.fetch("select discriminator from users where username=$1", username)
            discrims = [row["discriminator"] for row in users]
            diff = iter(all_discrims - set(discrims))
            discrim = next(diff)

            try:
                await conn.execute("insert into users(id, username, hashed_password, email, discriminator) values($1, $2, $3, $4, $5)", id, username, hashed, email, discrim)
            except asyncpg.exceptions.UniqueViolationError:
                raise CustomError

            return {"username": username, "discriminator": discrim, "email": email, "id": id}

    async def get_account(self, email, password, *, with_settings=False):
        async with self.accqire() as conn:
            row = await conn.fetchrow("select * from users where email=$1", email)

            if not row:
                raise CustomError
            try:
                self.hasher.verify(row["hashed_password"], password)
            except argon2.exceptions.VerificationError:
                raise CustomError

            row = dict(row)

            if with_settings:
                user_settings = await conn.fetchrow("select locale, theme from user_settings where user_id=$1", row["id"])
                if not user_settings:
                    user_settings = await conn.fetchrow("insert into user_settings(user_id) values ($1) returning theme, locale;", row["id"])

                row["user_settings"] = dict(user_settings)  # type: ignore

            return row
