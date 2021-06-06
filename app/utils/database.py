from __future__ import annotations

import asyncpg
import contextlib
import argon2
import ujson
from typing import Any, Optional, cast
import datetime

from .errors import CustomError
from .misc import filter_channel_keys

all_discrims: set[str] = set(str(d).rjust(4, "0") for d in range(1, 1000))

def now() -> str:
    return datetime.datetime.utcnow().isoformat()

class DB:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.hasher = argon2.PasswordHasher()

    @staticmethod
    async def connection_init(connection: asyncpg.Connection) -> asyncpg.Connection:
        await connection.set_type_codec("json", encoder=ujson.dumps, decoder=ujson.loads, schema="pg_catalog")
        return connection

    @classmethod
    async def from_args(cls, args: dict[str, str]):
        pool = await asyncpg.create_pool(**args, init=cls.connection_init)
        assert pool
        return cls(pool)

    @contextlib.asynccontextmanager
    async def accqire(self, conn: Optional[asyncpg.Connection] = None):
        release = True

        try:
            if conn is None:
                conn = cast(asyncpg.Connection, await self.pool.acquire())
            else:
                release = False  # we are already in a context manager so i wont release it here

            transaction = conn.transaction()
            if transaction._managed:

                yield conn
            else:
                async with transaction:
                    yield conn
        finally:
            if release:
                await self.pool.release(conn)

    async def create_account(self, username: str, email: str, password: str, id: str) -> dict[str, Any]:
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

    async def get_channel(self, channel_id: str, *, conn: Optional[asyncpg.Connection] = None, partial: bool = False) -> dict[str, Any]:
        if partial:
            columns = "id, name, type"
        else:
            columns = "*"

        async with self.accqire(conn) as conn:
            row = await conn.fetchrow(f"select {columns} from guild_channels where id=$1", channel_id)
        
        if not row:
            raise CustomError
        
        return filter_channel_keys(row)

    async def get_guild(self, guild_id: str, *, conn: Optional[asyncpg.Connection] = None, partial: bool = False) -> dict[str, Any]:
        if partial:
            columns = "id, name, splash, banner, description, icon, features, verification_level, vanity_url_code, nsfw"
        else:
            columns = "*"

        async with self.accqire(conn) as conn:
            row = await conn.fetchrow(f"select {columns} from guilds where id=$1", guild_id)
        
        if not row:
            raise CustomError
        
        return dict(row)

    async def get_guild_id_from_channel_id(self, channel_id: str, *, conn: Optional[asyncpg.Connection] = None) -> str:
        async with self.accqire(conn) as conn:
            guild_id: Optional[str] = await conn.fetchval("select guild_id from guild_channels where id=$1", channel_id)
            
            if not guild_id:
                raise CustomError
            
            return guild_id

    async def get_user(self, user_id: str, *, conn: Optional[asyncpg.Connection] = None) -> dict[str, Any]:
        async with self.accqire(conn) as conn:
            user = await conn.fetchrow("select username, discriminator, id, avatar from users where id=$1", user_id)

        if not user:
            raise CustomError

        return dict(user)
