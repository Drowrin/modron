DO $$ BEGIN
    CREATE TYPE game_status AS ENUM ('unstarted', 'running', 'paused', 'finished');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS Games (
    game_id SERIAL,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(4000) NOT NULL,
    system VARCHAR(35) NOT NULL,

    guild_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,

    status game_status NOT NULL DEFAULT 'unstarted',
    seeking_players BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (now() at time zone 'utc'),

    image VARCHAR(256),
    thumb VARCHAR(256),

    category_id BIGINT,
    main_channel_id BIGINT,
    info_channel_id BIGINT,
    schedule_channel_id BIGINT,
    synopsis_channel_id BIGINT,

    CONSTRAINT games_pk PRIMARY KEY (game_id),
    CONSTRAINT games_name_guild_unique UNIQUE (name, guild_id)
);

CREATE TABLE IF NOT EXISTS Characters (
    character_id SERIAL,
    game_id INT NOT NULL,
    author_id BIGINT NOT NULL,

    name VARCHAR(100) NOT NULL,
    pronouns VARCHAR(64),

    image VARCHAR(256),

    brief VARCHAR(256) NOT NULL,
    description VARCHAR(4096) NOT NULL,

    CONSTRAINT characters_pk PRIMARY KEY (character_id),
    CONSTRAINT characters_game_fk FOREIGN KEY (game_id) REFERENCES Games (game_id)
);

CREATE TABLE IF NOT EXISTS Players (
    user_id BIGINT,
    game_id INT,

    character_id INT,

    role VARCHAR(100) NOT NULL,

    CONSTRAINT players_pk PRIMARY KEY (user_id, game_id),
    CONSTRAINT players_game_fk FOREIGN KEY (game_id) REFERENCES Games (game_id),
    CONSTRAINT players_character_fk FOREIGN KEY (character_id) REFERENCES Characters (character_id)
);