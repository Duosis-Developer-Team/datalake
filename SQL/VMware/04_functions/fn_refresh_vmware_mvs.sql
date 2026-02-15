-- Refresh Function for VMware Materialized Views
-- Refreshes all VMware materialized views in correct order
-- Call this function every 15 minutes via pg_cron or scheduler

CREATE OR REPLACE FUNCTION refresh_vmware_materialized_views()
RETURNS TABLE(
    view_name TEXT,
    status TEXT,
    duration_ms BIGINT,
    refreshed_at TIMESTAMPTZ
) AS $$
DECLARE
    start_time TIMESTAMPTZ;
    end_time TIMESTAMPTZ;
    view_list TEXT[] := ARRAY[
        'mv_vmware_vm_latest',
        'mv_vmware_vm_metrics_latest',
        'mv_vmware_host_latest',
        'mv_vmware_host_metrics_latest',
        'mv_vmware_cluster_latest',
        'mv_vmware_datacenter_latest'
    ];
    v TEXT;
BEGIN
    FOREACH v IN ARRAY view_list
    LOOP
        BEGIN
            start_time := clock_timestamp();
            
            -- Refresh materialized view
            EXECUTE format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I', v);
            
            end_time := clock_timestamp();
            
            -- Return success record
            view_name := v;
            status := 'SUCCESS';
            duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
            refreshed_at := end_time;
            RETURN NEXT;
            
        EXCEPTION WHEN OTHERS THEN
            -- Return error record
            view_name := v;
            status := 'ERROR: ' || SQLERRM;
            duration_ms := NULL;
            refreshed_at := clock_timestamp();
            RETURN NEXT;
        END;
    END LOOP;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_vmware_materialized_views() IS 
    'Refreshes all VMware materialized views. Returns status for each view. 
     Run this every 15 minutes via pg_cron or external scheduler.';

-- ============================================================================
-- pg_cron Setup Instructions
-- ============================================================================

-- 1. Enable pg_cron extension (run once):
--    CREATE EXTENSION IF NOT EXISTS pg_cron;
--
-- 2. Schedule the refresh job (run once):
--    SELECT cron.schedule(
--        'refresh-vmware-mvs',
--        '*/15 * * * *',
--        'SELECT * FROM refresh_vmware_materialized_views();'
--    );
--
-- 3. View scheduled jobs:
--    SELECT * FROM cron.job WHERE jobname = 'refresh-vmware-mvs';
--
-- 4. View job run history:
--    SELECT * FROM cron.job_run_details 
--    WHERE jobid = (SELECT jobid FROM cron.job WHERE jobname = 'refresh-vmware-mvs')
--    ORDER BY start_time DESC LIMIT 10;
--
-- 5. Unschedule if needed:
--    SELECT cron.unschedule('refresh-vmware-mvs');

-- ============================================================================
-- Manual Refresh (for testing or immediate update)
-- ============================================================================

-- Refresh all views and see status:
-- SELECT * FROM refresh_vmware_materialized_views();
--
-- Refresh single view:
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_vmware_vm_latest;
