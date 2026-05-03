\restrict neg2ohmJRv3wArvR8lVXtgSexmIbLFbT2vM7tPeaKLdRLYKngvfECh8uLAszFa9
CREATE TABLE public.gui_crm_service_pages (
    page_key text NOT NULL,
    category_label text NOT NULL,
    gui_tab_binding text NOT NULL,
    resource_unit text DEFAULT 'Adet'::text NOT NULL,
    icon text,
    route_hint text,
    tab_hint text,
    sub_tab_hint text
);
ALTER TABLE ONLY public.gui_crm_service_pages
    ADD CONSTRAINT gui_crm_service_pages_pkey PRIMARY KEY (page_key);
\unrestrict neg2ohmJRv3wArvR8lVXtgSexmIbLFbT2vM7tPeaKLdRLYKngvfECh8uLAszFa9
