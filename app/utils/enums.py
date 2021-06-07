class ChannelType:
    text = 0
    dm = 1
    voice = 2
    dm = 3
    category = 4
    news = 5
    news_thread = 10
    public_thread = 11
    private_thread = 12
    stage = 13


tup = tuple[int, str]

class JsonErrors:
    general: tup = (0, "Invalid")
    missing_key: tup = (0, "Missing Required Key")

    unknown_channel: tup = (10003, "Uknown Channel")
    unknown_invite: tup = (10006, "Unknown Invite")

    missing_access: tup = (50001, "Missing Acess")
    invalid_form: tup = (50035, "Invalid Form Body")
    empty_message: tup = (50006, "Cannot Send An Empty Message")

class HTTPErrors:
    invalid_method: tup = (0, "405: Method Not Allowed")
    unauthorized: tup = (0, "401: Unauthorized")

class GatewayOps:
    dispatch: int = 0
    heartbeat: int = 1
    identify: int = 2
    presence_update: int = 3
    voice_state_update: int = 4
    resume: int = 6
    reconnect: int = 7
    request_guild_members: int = 8
    invalid_session: int = 9
    hello: int = 10
    heartbeat_ack: int = 11

class GatewayErrors:
    unknown: int = 4000
    bad_opcode: int = 4001
    decode_error: int = 4002
    not_authed: int = 4003
    auth_failed: int = 4004
    already_authed: int = 4005
    
    invalid_seq: int = 4007
    rate_limited: int = 4008  # :^)
    session_timed_out: int = 4009
    invalid_shard: int = 4010  # probably not going to be used
    sharding_required: int = 4011  # probably not going to be used
    invalid_version: int = 4012
    invalid_intents: int = 4013  # probably not going to be used
    disallowed_intent: int = 4014  # probably not going to be used

class MessageTypes:
    default = 0
