\restrict hAZe6gJEdbvlaTehukjIYcqZJ9fo4Gj8XrG2co2f3zSbpT3Qr6uhF0kyBYyYhgV
CREATE TABLE public.loki_platforms (
    id integer NOT NULL,
    url text,
    display_url text,
    display text,
    name text,
    slug text,
    manufacturer_id integer,
    manufacturer_url text,
    manufacturer_display text,
    manufacturer_name text,
    manufacturer_slug text,
    manufacturer_description text,
    config_template text,
    description text,
    tags jsonb,
    custom_fields_dc text,
    custom_fields_ip_addresses text,
    custom_fields_port text,
    custom_fields_site text,
    custom_fields_url text,
    created timestamp with time zone,
    last_updated timestamp with time zone,
    device_count integer,
    virtualmachine_count integer
);
ALTER TABLE ONLY public.loki_platforms
    ADD CONSTRAINT loki_platforms_pkey PRIMARY KEY (id);
\unrestrict hAZe6gJEdbvlaTehukjIYcqZJ9fo4Gj8XrG2co2f3zSbpT3Qr6uhF0kyBYyYhgV
