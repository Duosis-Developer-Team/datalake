\restrict 6LjUpULtFleKFvw9aFuwcaBLmJNvhlNFeFPlTyWbp87p6e7CNaLKGLbAtW9h3Jo
CREATE TABLE public.discovery_crm_salesorders (
    salesorderid text NOT NULL,
    data_type text DEFAULT 'crm_inventory_salesorder'::text NOT NULL,
    name text,
    ordernumber text,
    customerid text,
    customerid_name text,
    opportunityid text,
    quoteid text,
    ownerid text,
    owner_name text,
    totalamount double precision,
    totaltax double precision,
    totallineitemamount double precision,
    submitdate date,
    fulfilldate date,
    statecode bigint,
    statecode_text text,
    statuscode bigint,
    statuscode_text text,
    pricelevelid text,
    pricelevel_name text,
    transactioncurrencyid text,
    transactioncurrency_text text,
    createdon timestamp with time zone,
    modifiedon timestamp with time zone,
    collection_time timestamp with time zone
);
COMMENT ON TABLE public.discovery_crm_salesorders IS 'Dynamics 365 CRM sales orders. UPSERT on salesorderid.';
COMMENT ON COLUMN public.discovery_crm_salesorders.salesorderid IS 'CRM sales order GUID — primary key and UPSERT key.';
COMMENT ON COLUMN public.discovery_crm_salesorders.customerid IS 'FK account GUID.';
COMMENT ON COLUMN public.discovery_crm_salesorders.statecode IS 'Order state (0=Active, 1=Submitted, 2=Cancelled, 3=Fulfilled, 4=Invoiced).';
COMMENT ON COLUMN public.discovery_crm_salesorders.collection_time IS 'Timestamp of the discovery script run.';
ALTER TABLE ONLY public.discovery_crm_salesorders
    ADD CONSTRAINT discovery_crm_salesorders_pkey PRIMARY KEY (salesorderid);
CREATE INDEX idx_crm_so_customerid ON public.discovery_crm_salesorders USING btree (customerid);
CREATE INDEX idx_crm_so_modifiedon ON public.discovery_crm_salesorders USING btree (modifiedon);
CREATE INDEX idx_crm_so_statecode ON public.discovery_crm_salesorders USING btree (statecode);
\unrestrict 6LjUpULtFleKFvw9aFuwcaBLmJNvhlNFeFPlTyWbp87p6e7CNaLKGLbAtW9h3Jo
