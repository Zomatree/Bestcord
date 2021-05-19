CREATE TABLE user_settings (
    theme text NOT NULL DEFAULT 'dark',
    locale text NOT NULL DEFAULT 'en-GB',
    user_id text NOT NULL,
    CONSTRAINT user_settings_user_id_unique UNIQUE (user_id),
    CONSTRAINT user_settings_user_id_foreign FOREIGN KEY (user_id)
        REFERENCES public.users (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
        NOT VALID
);

CREATE TABLE users (
    username text NOT NULL,
    discriminator text NOT NULL,
    email text NOT NULL,
    hashed_password text,
    id text,
    CONSTRAINT users_email_unique UNIQUE (email),
    CONSTRAINT users_id_unique UNIQUE (id)
);
