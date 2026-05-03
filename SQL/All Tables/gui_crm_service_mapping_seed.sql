\restrict ZA8hF6DKrogqogNqrftDcPSrggPUdeom1gfYpdNGhFBowkMeWQz9MzjFWH7cxlc
CREATE TABLE public.gui_crm_service_mapping_seed (
    productid text NOT NULL,
    page_key text NOT NULL
);
ALTER TABLE ONLY public.gui_crm_service_mapping_seed
    ADD CONSTRAINT gui_crm_service_mapping_seed_pkey PRIMARY KEY (productid);
ALTER TABLE ONLY public.gui_crm_service_mapping_seed
    ADD CONSTRAINT gui_crm_service_mapping_seed_page_key_fkey FOREIGN KEY (page_key) REFERENCES public.gui_crm_service_pages(page_key);
\unrestrict ZA8hF6DKrogqogNqrftDcPSrggPUdeom1gfYpdNGhFBowkMeWQz9MzjFWH7cxlc
