CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS account(
    id UUID NOT NULL DEFAULT uuid_generate_v1() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT,
    name TEXT,
    blk_address TEXT,
    blk_password TEXT,
    is_admin BOOLEAN,
    recipient TEXT
    ); 

CREATE TABLE  IF NOT EXISTS session (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client UUID NOT NULL,
    value TEXT NOT NULL,
    token TEXT,
    status INTEGER default 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated TIMESTAMPTZ,
    CONSTRAINT session_user_id_fkey FOREIGN KEY (client)
        REFERENCES account (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE OR REPLACE FUNCTION trigger_set_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS set_timestamp on "session";
CREATE TRIGGER set_timestamp
    BEFORE UPDATE ON session
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TABLE IF NOT EXISTS encrypted_session(
        id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id INTEGER NOT NULL,
    cipher_name TEXT NOT NULL,
    cipher_mode TEXT NOT NULL,
    cipher_keylength INTEGER NOT NULL,   
    key TEXT NOT NULL, 
    encoding TEXT,        
    integrity_fun TEXT,
    CONSTRAINT encryption_session_id_fkey FOREIGN KEY (session_id) 
        REFERENCES session (id) MATCH SIMPLE
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS property (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property_name text NOT NULL,
    property_value text NOT NULL,
    UNIQUE (property_name, property_value)
);
INSERT INTO property (property_name, property_value)
        VALUES
          ('type', 'co2'),
          ('type', 'air quality'),
          ('type', 'temperature'),
          ('type', 'humidity'),
          ('type', 'particulate');


CREATE TABLE IF NOT EXISTS purpose_of_usage (
    id UUID UNIQUE NOT NULL PRIMARY KEY,
    subscriber UUID NOT NULL REFERENCES account (id),
    label TEXT, 
    url TEXT
);


CREATE TABLE  IF NOT EXISTS blk_transaction (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    hash text NOT NULL,
    params text,
    event_name text NOT NULL,
    client UUID NOT NULL,
    task INTEGER,
    uuid UUID,
    CONSTRAINT transaction_user_id_fkey FOREIGN KEY (client)
        REFERENCES account (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE IF NOT EXISTS product (
    id UUID NOT NULL DEFAULT uuid_generate_v1() ,
    label text NOT NULL,
    tariff_price MONEY DEFAULT 0,
    tariff_period INTEGER DEFAULT 0,
    data_origin_id TEXT,
    latitude TEXT,
    longitude TEXT,
    height INTEGER,
    elevation INTEGER,
    blk_address TEXT UNIQUE,
    city TEXT,
    address TEXT,
    status INTEGER DEFAULT 0,
    publisher UUID NOT NULL,
    connstring_hostname text,
    connstring_port text,
    connstring_protocol text,
    notes TEXT,
    sensor_type TEXT,
    secret text  NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    blk_specific TEXT,
    UNIQUE (id, label),
    CONSTRAINT id_tbl PRIMARY KEY ( id ),
    CONSTRAINT product_publisher_id_fkey FOREIGN KEY (publisher)
        REFERENCES account (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);



CREATE TABLE  IF NOT EXISTS products_subscribers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    subscriber_secret TEXT NOT NULL,
    subscriber UUID NOT NULL  REFERENCES account (id),
    product uuid NOT NULL REFERENCES product (id),
    granted INTEGER default 0,
    unique (product, subscriber)
);


CREATE TABLE IF NOT EXISTS product_subscription(
    id UUID NOT NULL PRIMARY KEY,
    subscriber UUID NOT NULL REFERENCES account (id),
    subscriber_secret TEXT NOT NULL,
    product uuid NOT NULL REFERENCES product (id),            
    purpose_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted INTEGER default 0,
    pending BOOLEAN default False,
    blk_address text,
    UNIQUE(id),
    UNIQUE(subscriber, product, purpose_id), 
    CONSTRAINT purpose_id_fkey FOREIGN KEY (purpose_id)
        REFERENCES purpose_of_usage  (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE  IF NOT EXISTS property_product (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    property INTEGER NOT NULL REFERENCES property (id),
    product UUID NOT NULL REFERENCES product (id)
);


CREATE TABLE IF NOT EXISTS product_usage (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id UUID NOT NULL ,
    account_id UUID NOT NULL,
    usage INTEGER NOT NULL,
    CONSTRAINT product_id_pukey FOREIGN KEY (product_id)
        REFERENCES product (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT account_id_pukey FOREIGN KEY (account_id)
        REFERENCES account (id) MATCH SIMPLE
        ON UPDATE NO ACTION ON DELETE NO ACTION
);
