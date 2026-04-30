-- Align v_gui_crm_product_mapping with line-level UoM (salesorderdetails.uomid_name)
-- and re-classify Klasik Mimari replication SKUs to backup_* (see embedded_rules.json).
BEGIN;

CREATE OR REPLACE VIEW v_gui_crm_product_mapping AS
SELECT
    pr.productid,
    pr.name AS product_name,
    pr.productnumber AS product_number,
    COALESCE(o.page_key, s.page_key, 'other') AS category_code,
    pg.category_label,
    pg.gui_tab_binding,
    NULL::text AS resource_unit,
    CASE WHEN o.productid IS NOT NULL THEN 'override' WHEN s.productid IS NOT NULL THEN 'yaml' ELSE 'default' END AS mapping_source,
    COALESCE(NULLIF(TRIM(pg.resource_unit), ''), 'Adet') AS page_resource_unit
FROM   discovery_crm_products pr
LEFT JOIN gui_crm_service_mapping_seed s ON s.productid = pr.productid
LEFT JOIN gui_crm_service_mapping_override o ON o.productid = pr.productid
JOIN   gui_crm_service_pages pg ON pg.page_key = COALESCE(o.page_key, s.page_key, 'other');

-- Seed-only: move Klasik replication products from virt_classic to backup_* (no operator override touched).
UPDATE gui_crm_service_mapping_seed s
SET    page_key = 'backup_veeam'
FROM   discovery_crm_products p
WHERE  s.productid = p.productid
  AND  s.page_key = 'virt_classic'
  AND  p.name ~* 'Klasik Mimari Veeam Replication';

UPDATE gui_crm_service_mapping_seed s
SET    page_key = 'backup_zerto'
FROM   discovery_crm_products p
WHERE  s.productid = p.productid
  AND  s.page_key = 'virt_classic'
  AND  p.name ~* 'Klasik Mimari Zerto Replication';

COMMIT;
