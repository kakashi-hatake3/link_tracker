--liquibase formatted sql

--changeset kakashi-hatake3:1
CREATE TABLE chats (
    chat_id INT PRIMARY KEY
);

--changeset kakashi-hatake3:2
CREATE TABLE links (
    id SERIAL PRIMARY KEY,
    chat_id INT NOT NULL,
    url VARCHAR(255) NOT NULL,
    CONSTRAINT fk_links_chat FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
);

--changeset kakashi-hatake3:3
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

--changeset kakashi-hatake3:4
CREATE TABLE filters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

--changeset kakashi-hatake3:5
CREATE TABLE link_tags (
    link_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (link_id, tag_id),
    CONSTRAINT fk_link_tags_link FOREIGN KEY (link_id) REFERENCES links(id),
    CONSTRAINT fk_link_tags_tag FOREIGN KEY (tag_id) REFERENCES tags(id)
);

--changeset kakashi-hatake3:6
CREATE TABLE link_filters (
    link_id INT NOT NULL,
    filter_id INT NOT NULL,
    PRIMARY KEY (link_id, filter_id),
    CONSTRAINT fk_link_filters_link FOREIGN KEY (link_id) REFERENCES links(id),
    CONSTRAINT fk_link_filters_filter FOREIGN KEY (filter_id) REFERENCES filters(id)
);
