\restrict l93IaKDtiHHlwjAucWVE0ed7N7KVtBAfR2dGPVnmvE4rJSdpMEE4jUwMXf4BlnJ
CREATE TABLE public.discovery_ibm_inventory (
    asset_type character varying(50),
    servername character varying(255),
    asset_name character varying(255),
    mtm character varying(255),
    state character varying(100),
    os_type character varying(100),
    asset_id character varying(100),
    collection_time timestamp with time zone
);
ALTER TABLE ONLY public.discovery_ibm_inventory
    ADD CONSTRAINT discovery_ibm_inventory_unq UNIQUE (asset_name, asset_type);
\unrestrict l93IaKDtiHHlwjAucWVE0ed7N7KVtBAfR2dGPVnmvE4rJSdpMEE4jUwMXf4BlnJ
