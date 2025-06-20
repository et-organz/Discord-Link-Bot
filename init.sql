CREATE TYPE reaction_tuple AS (
    emoji TEXT,
    user_id BIGINT
);

CREATE TABLE link_messages (
    id SERIAL PRIMARY KEY,
    message_id BIGINT UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    link TEXT NOT NULL,
    domain_name TEXT NOT NULL,
    reactions reaction_tuple[],
    reactors BIGINT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE media_messages (
    id SERIAL PRIMARY KEY,
    message_id BIGINT UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    media_url TEXT NOT NULL,
    media_type TEXT NOT NULL,
    reactions reaction_tuple[],
    reactors BIGINT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);