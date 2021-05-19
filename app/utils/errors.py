class CustomError(Exception):
    pass

class JsonErrors:
    general = (0, "Invalid")
    missing_key = (0, "Missing Required Key")
    invalid_form = (50035, "Invalid Form Body")

class HTTPErrors:
    invalid_method = (0, "405: Method Not Allowed")
    unauthorized = (0, "401: Unauthorized")

class GatewayOps:
    dispatch = 0
    heartbeat = 1
    identify = 2
    presence_update = 3
    voice_state_update = 4
    resume = 5
    reconnect = 6
    request_guild_members = 7
    invalid_session = 9
    hello = 10
    heartbeat_ack = 11

class GatewayErrors:
    unknown = 4000
    bad_opcode = 4001
    decode_error = 4002
    not_authed = 4003
    auth_failed = 4004
    already_authed = 4005
    
    invalid_seq = 4007
    rate_limited = 4008  # :^)
    session_timed_out = 4009
    invalid_shard = 4010  # probably not going to be used
    sharding_required = 4011  # probably not going to be used
    invalid_version = 4012
    invalid_intents = 4013  # probably not going to be used
    disallowed_intent = 4014  # probably not going to be used
