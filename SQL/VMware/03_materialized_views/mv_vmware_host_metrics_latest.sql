SELECT cron.schedule(
      'refresh-vmware-mvs',
      '*/15 * * * *',
      'SELECT * FROM refresh_vmware_materialized_views();'
    );


CREATE EXTENSION IF NOT EXISTS pg_cron;