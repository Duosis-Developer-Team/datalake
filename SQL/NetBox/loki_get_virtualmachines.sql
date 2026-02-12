-- NetBox virtualization VM inventory table for loki_get_virtualmachines.py
-- This table is designed for UPSERT (insert-or-update) semantics on the NetBox VM id.

CREATE TABLE IF NOT EXISTS public.netbox_virtualization_vm (
    -- Primary identification
    id                   BIGINT PRIMARY KEY,
    data_type            TEXT,
    count                BIGINT,

    -- Core VM identity
    url                  TEXT,
    display_url          TEXT,
    display              TEXT,
    name                 TEXT,

    -- Status
    status_value         TEXT,
    status_label         TEXT,

    -- Site information
    site_id              BIGINT,
    site_url             TEXT,
    site_display         TEXT,
    site_name            TEXT,
    site_slug            TEXT,
    site_description     TEXT,

    -- Cluster information
    cluster_id           BIGINT,
    cluster_url          TEXT,
    cluster_display      TEXT,
    cluster_name         TEXT,
    cluster_description  TEXT,

    -- Device (host) information
    device_id            BIGINT,
    device_url           TEXT,
    device_display       TEXT,
    device_name          TEXT,
    device_description   TEXT,

    -- VM attributes
    serial               TEXT,
    role                 TEXT,
    tenant               TEXT,
    platform             TEXT,

    primary_ip           TEXT,
    primary_ip4          TEXT,
    primary_ip6          TEXT,

    vcpus                BIGINT,
    memory               BIGINT,
    disk                 BIGINT,

    description          TEXT,
    comments             TEXT,
    config_template      TEXT,
    local_context_data   TEXT,
    config_context       TEXT,

    -- Tags (up to 5 tags flattened)
    tags1_id             BIGINT,
    tags1_url            TEXT,
    tags1_display_url    TEXT,
    tags1_display        TEXT,
    tags1_name           TEXT,
    tags1_slug           TEXT,
    tags1_color          TEXT,

    tags2_id             BIGINT,
    tags2_url            TEXT,
    tags2_display_url    TEXT,
    tags2_display        TEXT,
    tags2_name           TEXT,
    tags2_slug           TEXT,
    tags2_color          TEXT,

    tags3_id             BIGINT,
    tags3_url            TEXT,
    tags3_display_url    TEXT,
    tags3_display        TEXT,
    tags3_name           TEXT,
    tags3_slug           TEXT,
    tags3_color          TEXT,

    tags4_id             BIGINT,
    tags4_url            TEXT,
    tags4_display_url    TEXT,
    tags4_display        TEXT,
    tags4_name           TEXT,
    tags4_slug           TEXT,
    tags4_color          TEXT,

    tags5_id             BIGINT,
    tags5_url            TEXT,
    tags5_display_url    TEXT,
    tags5_display        TEXT,
    tags5_name           TEXT,
    tags5_slug           TEXT,
    tags5_color          TEXT,

    -- Custom fields
    custom_fields_config_instance_uuid   TEXT,
    custom_fields_config_uuid           TEXT,
    custom_fields_datastore_name        TEXT,
    custom_fields_endpoint              TEXT,
    custom_fields_guest_os              TEXT,

    custom_fields_hard_disk_info1_label       TEXT,
    custom_fields_hard_disk_info1_backing     TEXT,
    custom_fields_hard_disk_info1_capacity_kb BIGINT,

    custom_fields_hard_disk_info2_label       TEXT,
    custom_fields_hard_disk_info2_backing     TEXT,
    custom_fields_hard_disk_info2_capacity_kb BIGINT,

    custom_fields_hard_disk_info3_label       TEXT,
    custom_fields_hard_disk_info3_backing     TEXT,
    custom_fields_hard_disk_info3_capacity_kb BIGINT,

    custom_fields_hard_disk_info4_label       TEXT,
    custom_fields_hard_disk_info4_backing     TEXT,
    custom_fields_hard_disk_info4_capacity_kb BIGINT,

    custom_fields_hard_disk_info5_label       TEXT,
    custom_fields_hard_disk_info5_backing     TEXT,
    custom_fields_hard_disk_info5_capacity_kb BIGINT,

    custom_fields_ip_addresses         TEXT,
    custom_fields_moid                 TEXT,
    custom_fields_musteri              TEXT,
    custom_fields_price_id             TEXT,
    custom_fields_uuid                 TEXT,
    custom_fields_vm_name              TEXT,
    custom_fields_vm_olusturulma_tarihi TEXT,
    custom_fields_vmx_path             TEXT,

    created               TIMESTAMPTZ,
    last_updated          TIMESTAMPTZ,

    interface_count       BIGINT,
    virtual_disk_count    BIGINT,

    collection_time       TIMESTAMPTZ
);

-- Optional indexes for common lookup and join patterns
CREATE INDEX IF NOT EXISTS idx_netbox_virtualization_vm_custom_fields_uuid
    ON public.netbox_virtualization_vm (custom_fields_uuid);

CREATE INDEX IF NOT EXISTS idx_netbox_virtualization_vm_site_id
    ON public.netbox_virtualization_vm (site_id);

