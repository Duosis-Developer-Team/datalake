\restrict vv0Rx3fcTmTxUboTsOaURX0JRnowTu5WVM4OmGjb2JECyDeuiV47WVexG1VgKUT
CREATE TABLE public.discovery_crm_pricelevels (
    pricelevelid text NOT NULL,
    data_type text DEFAULT 'crm_inventory_pricelevel'::text NOT NULL,
    name text,
    transactioncurrencyid text,
    transactioncurrency_text text,
    exchangerate double precision,
    begindate date,
    enddate date,
    statecode bigint,
    statecode_text text,
    createdon timestamp with time zone,
    modifiedon timestamp with time zone,
    collection_time timestamp with time zone
);
COMMENT ON TABLE public.discovery_crm_pricelevels IS 'Dynamics 365 CRM price lists (pricelevels). UPSERT on pricelevelid.';
COMMENT ON COLUMN public.discovery_crm_pricelevels.pricelevelid IS 'CRM price level GUID — primary key and UPSERT key.';
COMMENT ON COLUMN public.discovery_crm_pricelevels.name IS 'Price list name (e.g. TL Fiyat Listesi, USD Fiyat Listesi).';
COMMENT ON COLUMN public.discovery_crm_pricelevels.exchangerate IS 'Exchange rate relative to base currency at time of last modification.';
COMMENT ON COLUMN public.discovery_crm_pricelevels.collection_time IS 'Timestamp of the discovery script run.';
ALTER TABLE ONLY public.discovery_crm_pricelevels
    ADD CONSTRAINT discovery_crm_pricelevels_pkey PRIMARY KEY (pricelevelid);
CREATE INDEX idx_crm_pricelevels_modifiedon ON public.discovery_crm_pricelevels USING btree (modifiedon);
CREATE INDEX idx_crm_pricelevels_name ON public.discovery_crm_pricelevels USING btree (name);
\unrestrict vv0Rx3fcTmTxUboTsOaURX0JRnowTu5WVM4OmGjb2JECyDeuiV47WVexG1VgKUT
