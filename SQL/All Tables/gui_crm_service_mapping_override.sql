\restrict XZTSdbJ2XMaQNjCTvGT6QPRWBLpZOZWIjnQgVKrtJCAx6XQxOvCxGIjRmwSuWNo
CREATE TABLE public.gui_crm_service_mapping_override (
    productid text NOT NULL,
    page_key text NOT NULL,
    notes text,
    updated_by text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);
ALTER TABLE ONLY public.gui_crm_service_mapping_override
    ADD CONSTRAINT gui_crm_service_mapping_override_pkey PRIMARY KEY (productid);
ALTER TABLE ONLY public.gui_crm_service_mapping_override
    ADD CONSTRAINT gui_crm_service_mapping_override_page_key_fkey FOREIGN KEY (page_key) REFERENCES public.gui_crm_service_pages(page_key);
\unrestrict XZTSdbJ2XMaQNjCTvGT6QPRWBLpZOZWIjnQgVKrtJCAx6XQxOvCxGIjRmwSuWNo
