create table users
(
	username text not null,
	discriminator text not null,
	email text not null
		constraint email
			unique,
	hashed_password text,
	id text not null
		constraint users_pk
			primary key
		constraint users_id_unique
			unique
);

create table user_settings
(
	theme text default 'dark'::text not null,
	locale text default 'en-GB'::text not null,
	user_id text not null
		constraint user_settings_pk
			primary key
		constraint user_id
			unique
		constraint user_settings_user_id_foreign
			references users (id)
				on delete cascade
);

create table guilds
(
	name text not null,
	owner_id text not null,
	id text not null
		constraint guilds_pkey
			primary key,
	icon text,
	splash text,
	afk_channel_id text,
	afk_timeout integer default 300 not null,
	verification_level integer default 0 not null,
	default_message_notifications integer default 0 not null,
	mfa_level integer default 0 not null,
	explicit_content_filter integer default 0,
	application_id text,
	system_channel_id text,
	system_channel_flags integer default 0 not null,
	rules_channel_id text,
	large boolean default false,
	unavailable boolean default false,
	member_count integer default 1,
	vanity_url_code text,
	description text,
	premium_tier integer default 3,
	premium_subscription_count integer default 999,
	preferred_locale text default 'en-US'::text,
	public_updates_channel_id text,
	nsfw boolean default false,
	features text[] default ARRAY[]::text[] not null
);

create table guild_members
(
	user_id text not null,
	guild_id text not null,
	joined_at timestamp with time zone default now() not null,
	deaf boolean default false not null,
	mute boolean default false not null,
	pending boolean default false not null,
	nick text,
	constraint guild_members_pkey
		primary key (user_id, guild_id)
);

create table guild_roles
(
	id text not null,
	name text not null,
	color integer default 16777215,
	hoist boolean default false not null,
	position integer not null,
	permissions text default 0 not null,
	managed boolean default false,
	mentionable boolean default false not null,
	guild_id text not null
		constraint guild_roles_pk
			primary key
		constraint guild_roles_guild_id_guilds
			references guilds
				on delete cascade
);

create unique index guild_roles_id_uindex
	on guild_roles (id);

create table guild_channels
(
	name text not null,
	id text not null
		constraint guild_channels_pk
			primary key,
	type integer default 0 not null,
	topic text default ''::text,
	bitrate integer default 0 not null,
	user_limit integer default 0 not null,
	rate_limit_per_user integer default 0 not null,
	position integer not null,
	parent_id text,
	nsfw boolean default false not null,
	guild_id text not null
		constraint guild_channels_guild_id_guilds
			references guilds
				on delete cascade
);

create unique index guild_channels_id_uindex
	on guild_channels (id);

create table messages
(
	id text not null
		constraint messages_pk
			primary key,
	content text,
	embeds json,
	tts boolean default false not null,
	allowed_mentions jsonb,
	channel_id text
		constraint messages_channel_id_guild_messages
			references guild_channels
				on delete cascade
);

create unique index messages_id_uindex
	on messages (id);
