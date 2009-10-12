BEGIN;

CREATE TABLE commits (
    id CHAR[40] PRIMARY KEY,
    time FLOAT,
    data TEXT
);

CREATE INDEX commits_time ON commits(time);

END;
