\restrict kAk3GqHanNldhwmkODkU4yhrRL8eDuPBO6Pu4Yzejiqkuc45JWye8APOxzDU45G
CREATE TABLE public.discovery_crm_products (
    productid text NOT NULL,
    data_type text DEFAULT 'crm_inventory_product'::text NOT NULL,
    name text,
    productnumber text,
    statecode bigint,
    statecode_text text,
    statuscode bigint,
    statuscode_text text,
    defaultuomid text,
    defaultuomid_name text,
    currentcost double precision,
    standardcost double precision,
    pricelevelid text,
    pricelevel_name text,
    blt_productgroup bigint,
    blt_productgroup_text text,
    blt_productmodel bigint,
    blt_productmodel_text text,
    blt_sectionorder bigint,
    createdon timestamp with time zone,
    modifiedon timestamp with time zone,
    collection_time timestamp with time zone
);
COMMENT ON TABLE public.discovery_crm_products IS 'Dynamics 365 CRM product catalog entries. UPSERT on productid.';
COMMENT ON COLUMN public.discovery_crm_products.productid IS 'CRM product GUID — primary key and UPSERT key.';
COMMENT ON COLUMN public.discovery_crm_products.productnumber IS 'Internal product SKU/number.';
COMMENT ON COLUMN public.discovery_crm_products.standardcost IS 'Standard cost in base currency.';
COMMENT ON COLUMN public.discovery_crm_products.blt_productgroup_text IS 'Custom product group label (Bulutistan extension).';
COMMENT ON COLUMN public.discovery_crm_products.blt_productmodel_text IS 'Custom product model label (Bulutistan extension).';
COMMENT ON COLUMN public.discovery_crm_products.collection_time IS 'Timestamp of the discovery script run.';
ALTER TABLE ONLY public.discovery_crm_products
    ADD CONSTRAINT discovery_crm_products_pkey PRIMARY KEY (productid);
CREATE INDEX idx_crm_products_modifiedon ON public.discovery_crm_products USING btree (modifiedon);
CREATE INDEX idx_crm_products_name ON public.discovery_crm_products USING btree (name);
\unrestrict kAk3GqHanNldhwmkODkU4yhrRL8eDuPBO6Pu4Yzejiqkuc45JWye8APOxzDU45G
