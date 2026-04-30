-- Audit CRM service mapping coverage (run in discovery DB).
-- Products with no seed and no override appear as category_code = other via the view join.

SELECT pr.productid,
       pr.productnumber,
       pr.name,
       COALESCE(o.page_key, s.page_key, 'other') AS effective_page_key,
       CASE WHEN o.productid IS NOT NULL THEN 'override'
            WHEN s.productid IS NOT NULL THEN 'seed'
            ELSE 'missing' END AS mapping_layer
FROM   discovery_crm_products pr
LEFT JOIN gui_crm_service_mapping_seed s ON s.productid = pr.productid
LEFT JOIN gui_crm_service_mapping_override o ON o.productid = pr.productid
WHERE  pr.statecode = 0
ORDER BY mapping_layer DESC, pr.name NULLS LAST;

-- Optional: products that sold in last 12 months but map to other (prioritize manual review).

WITH recent AS (
    SELECT DISTINCT d.productid
    FROM   discovery_crm_salesorderdetails d
    JOIN   discovery_crm_salesorders so ON so.salesorderid = d.salesorderid
    WHERE  so.statecode IN (3, 4)
      AND  COALESCE(so.fulfilldate::date, so.submitdate::date, so.modifiedon::date)
           >= CURRENT_DATE - INTERVAL '12 months'
)
SELECT pr.productid,
       pr.name,
       COALESCE(o.page_key, s.page_key, 'other') AS effective_page_key
FROM   recent r
JOIN   discovery_crm_products pr ON pr.productid = r.productid
LEFT JOIN gui_crm_service_mapping_seed s ON s.productid = pr.productid
LEFT JOIN gui_crm_service_mapping_override o ON o.productid = pr.productid
WHERE  COALESCE(o.page_key, s.page_key, 'other') = 'other'
ORDER BY pr.name NULLS LAST;
