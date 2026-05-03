\restrict BS5U0hEBa3uMXnJFikAvd3XLOvumO7MRYnvdYgECgfDdaGd5nsis12NnsvjVbGf
CREATE TABLE public.discovery_crm_productpricelevels (
    productpricelevelid text NOT NULL,
    data_type text DEFAULT 'crm_inventory_productpricelevel'::text NOT NULL,
    pricelevelid text,
    pricelevel_name text,
    productid text,
    product_name text,
    uomid text,
    uomid_name text,
    amount double precision,
    discounttypeid text,
    pricingmethodcode bigint,
    pricingmethodcode_text text,
    transactioncurrencyid text,
    transactioncurrency_text text,
    modifiedon timestamp with time zone,
    collection_time timestamp with time zone
);
COMMENT ON TABLE public.discovery_crm_productpricelevels IS 'Per-product unit price within a price list. Key join table for catalog valuation. UPSERT on productpricelevelid.';
COMMENT ON COLUMN public.discovery_crm_productpricelevels.productpricelevelid IS 'CRM product-price-level GUID — primary key and UPSERT key.';
COMMENT ON COLUMN public.discovery_crm_productpricelevels.pricelevelid IS 'FK to discovery_crm_pricelevels.';
COMMENT ON COLUMN public.discovery_crm_productpricelevels.productid IS 'FK to discovery_crm_products.';
COMMENT ON COLUMN public.discovery_crm_productpricelevels.uomid_name IS 'Unit of measure name (Adet, GB, vCPU, etc.).';
COMMENT ON COLUMN public.discovery_crm_productpricelevels.amount IS 'Unit price in transaction currency.';
COMMENT ON COLUMN public.discovery_crm_productpricelevels.collection_time IS 'Timestamp of the discovery script run.';
ALTER TABLE ONLY public.discovery_crm_productpricelevels
    ADD CONSTRAINT discovery_crm_productpricelevels_pkey PRIMARY KEY (productpricelevelid);
CREATE INDEX idx_crm_ppl_modifiedon ON public.discovery_crm_productpricelevels USING btree (modifiedon);
CREATE INDEX idx_crm_ppl_pricelevelid ON public.discovery_crm_productpricelevels USING btree (pricelevelid);
CREATE INDEX idx_crm_ppl_productid ON public.discovery_crm_productpricelevels USING btree (productid);
\unrestrict BS5U0hEBa3uMXnJFikAvd3XLOvumO7MRYnvdYgECgfDdaGd5nsis12NnsvjVbGf
