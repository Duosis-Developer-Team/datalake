\restrict 4GeE8Dkb70fZHvTB1Sp050ph0SyVKGxlBm0OpDEXa93XTL9mdhWcJvkzr7loq9S
CREATE TABLE public.discovery_crm_salesorderdetails (
    salesorderdetailid text NOT NULL,
    data_type text DEFAULT 'crm_inventory_salesorderdetail'::text NOT NULL,
    salesorderid text,
    productid text,
    product_name text,
    productdescription text,
    uomid text,
    uomid_name text,
    quantity double precision,
    priceperunit double precision,
    baseamount double precision,
    extendedamount double precision,
    manualdiscountamount double precision,
    transactioncurrencyid text,
    transactioncurrency_text text,
    modifiedon timestamp with time zone,
    collection_time timestamp with time zone
);
COMMENT ON TABLE public.discovery_crm_salesorderdetails IS 'Dynamics 365 CRM sales order line items. UPSERT on salesorderdetailid.';
COMMENT ON COLUMN public.discovery_crm_salesorderdetails.salesorderdetailid IS 'Primary key and UPSERT key.';
COMMENT ON COLUMN public.discovery_crm_salesorderdetails.salesorderid IS 'FK to discovery_crm_salesorders.';
COMMENT ON COLUMN public.discovery_crm_salesorderdetails.productid IS 'FK to discovery_crm_products.';
COMMENT ON COLUMN public.discovery_crm_salesorderdetails.extendedamount IS 'Total line amount.';
COMMENT ON COLUMN public.discovery_crm_salesorderdetails.collection_time IS 'Timestamp of the discovery script run.';
ALTER TABLE ONLY public.discovery_crm_salesorderdetails
    ADD CONSTRAINT discovery_crm_salesorderdetails_pkey PRIMARY KEY (salesorderdetailid);
CREATE INDEX idx_crm_sod_productid ON public.discovery_crm_salesorderdetails USING btree (productid);
CREATE INDEX idx_crm_sod_salesorderid ON public.discovery_crm_salesorderdetails USING btree (salesorderid);
\unrestrict 4GeE8Dkb70fZHvTB1Sp050ph0SyVKGxlBm0OpDEXa93XTL9mdhWcJvkzr7loq9S
