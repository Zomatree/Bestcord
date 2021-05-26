class Permissions:
    create_invite: int = 1 << 0
    kick_members: int = 1 << 1
    ban_members: int = 1 << 2
    admin: int = 1 << 3
    manage_channels: int = 1 << 4
    manage_guild: int = 1 << 5
    add_reactions: int = 1 << 6
    view_audit_log: int = 1 << 7
    priority_speaker: int = 1 << 8
    stream: int = 1 << 9
    view_channel: int = 1 << 10
    send_messages: int = 1 << 11
    send_tts_messages: int = 1 << 12
    manage_messages: int = 1 << 13
    embed_links: int = 1 << 14
    attach_files: int = 1 << 15
    read_message_history: int = 1 << 16
    mention_everyone: int = 1 << 17
    use_external_emojis: int = 1 << 18
    view_guild_insights: int = 1 << 19
    connect: int = 1 << 20
    speak: int = 1 << 21
    mute_members: int = 1 << 22
    deafen_members: int = 1 << 23
    move_members: int = 1 << 24
    use_voice_activity: int = 1 << 25
    change_nicks: int = 1 << 26
    manage_nicks: int = 1 << 27
    manage_roles: int = 1 << 28
    manage_webhooks: int = 1 << 29
    manage_emojis: int = 1 << 30
    use_slash_commands: int = 1 << 31
    request_to_speak: int = 1 << 32
    manage_threads: int = 1 << 33
    use_public_threads: int = 1 << 35
    use_private_threads: int = 1 << 36

    @staticmethod
    def all() -> int:
        return 0b111111111111111111111111111111111111
