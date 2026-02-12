-- VMware VM Metrics View
-- Pivoted aggregated performance metrics for each VM at each collection timestamp
-- Purpose: Single row per VM per timestamp with all key metrics as columns

CREATE OR REPLACE VIEW vmware_vm_metrics AS
WITH pivoted_metrics AS (
    SELECT 
        collection_timestamp,
        vcenter_uuid,
        vm_moid,
        window_start,
        window_end,
        window_duration_seconds,
        
        -- CPU Metrics (MHz)
        MAX(CASE WHEN counter_name = 'cpu.usage.average' AND instance = '' THEN value_avg END) AS cpu_usage_avg_mhz,
        MAX(CASE WHEN counter_name = 'cpu.usage.average' AND instance = '' THEN value_min END) AS cpu_usage_min_mhz,
        MAX(CASE WHEN counter_name = 'cpu.usage.average' AND instance = '' THEN value_max END) AS cpu_usage_max_mhz,
        
        MAX(CASE WHEN counter_name = 'cpu.usagemhz.average' AND instance = '' THEN value_avg END) AS cpu_usagemhz_avg,
        MAX(CASE WHEN counter_name = 'cpu.usagemhz.average' AND instance = '' THEN value_min END) AS cpu_usagemhz_min,
        MAX(CASE WHEN counter_name = 'cpu.usagemhz.average' AND instance = '' THEN value_max END) AS cpu_usagemhz_max,
        
        MAX(CASE WHEN counter_name = 'cpu.ready.average' AND instance = '' THEN value_avg END) AS cpu_ready_avg_ms,
        MAX(CASE WHEN counter_name = 'cpu.ready.average' AND instance = '' THEN value_max END) AS cpu_ready_max_ms,
        
        -- Memory Metrics (Percent scaled to 0-100)
        MAX(CASE WHEN counter_name = 'mem.usage.average' AND instance = '' THEN value_avg / 100.0 END) AS mem_usage_avg_percent,
        MAX(CASE WHEN counter_name = 'mem.usage.average' AND instance = '' THEN value_min / 100.0 END) AS mem_usage_min_percent,
        MAX(CASE WHEN counter_name = 'mem.usage.average' AND instance = '' THEN value_max / 100.0 END) AS mem_usage_max_percent,
        
        MAX(CASE WHEN counter_name = 'mem.consumed.average' AND instance = '' THEN value_avg END) AS mem_consumed_avg_kb,
        MAX(CASE WHEN counter_name = 'mem.consumed.average' AND instance = '' THEN value_max END) AS mem_consumed_max_kb,
        
        MAX(CASE WHEN counter_name = 'mem.active.average' AND instance = '' THEN value_avg END) AS mem_active_avg_kb,
        MAX(CASE WHEN counter_name = 'mem.active.average' AND instance = '' THEN value_max END) AS mem_active_max_kb,
        
        MAX(CASE WHEN counter_name = 'mem.swapped.average' AND instance = '' THEN value_avg END) AS mem_swapped_avg_kb,
        MAX(CASE WHEN counter_name = 'mem.swapped.average' AND instance = '' THEN value_max END) AS mem_swapped_max_kb,
        
        MAX(CASE WHEN counter_name = 'mem.vmmemctl.average' AND instance = '' THEN value_avg END) AS mem_balloon_avg_kb,
        MAX(CASE WHEN counter_name = 'mem.vmmemctl.average' AND instance = '' THEN value_max END) AS mem_balloon_max_kb,
        
        -- Disk I/O Metrics (KBps)
        MAX(CASE WHEN counter_name = 'disk.usage.average' AND instance = '' THEN value_avg END) AS disk_usage_avg_kbps,
        MAX(CASE WHEN counter_name = 'disk.usage.average' AND instance = '' THEN value_max END) AS disk_usage_max_kbps,
        
        MAX(CASE WHEN counter_name = 'disk.read.average' AND instance = '' THEN value_avg END) AS disk_read_avg_kbps,
        MAX(CASE WHEN counter_name = 'disk.read.average' AND instance = '' THEN value_max END) AS disk_read_max_kbps,
        
        MAX(CASE WHEN counter_name = 'disk.write.average' AND instance = '' THEN value_avg END) AS disk_write_avg_kbps,
        MAX(CASE WHEN counter_name = 'disk.write.average' AND instance = '' THEN value_max END) AS disk_write_max_kbps,
        
        -- Disk Latency (ms)
        MAX(CASE WHEN counter_name = 'disk.totalReadLatency.average' AND instance = '' THEN value_avg END) AS disk_read_latency_avg_ms,
        MAX(CASE WHEN counter_name = 'disk.totalReadLatency.average' AND instance = '' THEN value_max END) AS disk_read_latency_max_ms,
        
        MAX(CASE WHEN counter_name = 'disk.totalWriteLatency.average' AND instance = '' THEN value_avg END) AS disk_write_latency_avg_ms,
        MAX(CASE WHEN counter_name = 'disk.totalWriteLatency.average' AND instance = '' THEN value_max END) AS disk_write_latency_max_ms,
        
        -- Network Metrics (KBps)
        MAX(CASE WHEN counter_name = 'net.usage.average' AND instance = '' THEN value_avg END) AS net_usage_avg_kbps,
        MAX(CASE WHEN counter_name = 'net.usage.average' AND instance = '' THEN value_max END) AS net_usage_max_kbps,
        
        MAX(CASE WHEN counter_name = 'net.transmitted.average' AND instance = '' THEN value_avg END) AS net_tx_avg_kbps,
        MAX(CASE WHEN counter_name = 'net.transmitted.average' AND instance = '' THEN value_max END) AS net_tx_max_kbps,
        
        MAX(CASE WHEN counter_name = 'net.received.average' AND instance = '' THEN value_avg END) AS net_rx_avg_kbps,
        MAX(CASE WHEN counter_name = 'net.received.average' AND instance = '' THEN value_max END) AS net_rx_max_kbps,
        
        -- Network Packets (count/sec)
        MAX(CASE WHEN counter_name = 'net.packetsRx.average' AND instance = '' THEN value_avg END) AS net_packets_rx_avg,
        MAX(CASE WHEN counter_name = 'net.packetsTx.average' AND instance = '' THEN value_avg END) AS net_packets_tx_avg,
        
        -- Datastore Metrics (ms)
        MAX(CASE WHEN counter_name = 'datastore.read.average' AND instance = '*' THEN value_avg END) AS datastore_read_avg_kbps,
        MAX(CASE WHEN counter_name = 'datastore.write.average' AND instance = '*' THEN value_avg END) AS datastore_write_avg_kbps,
        
        MAX(CASE WHEN counter_name = 'datastore.numberReadAveraged.average' AND instance = '*' THEN value_avg END) AS datastore_read_iops_avg,
        MAX(CASE WHEN counter_name = 'datastore.numberWriteAveraged.average' AND instance = '*' THEN value_avg END) AS datastore_write_iops_avg,
        
        -- Sample count for quality assessment
        MAX(sample_count) AS max_sample_count
        
    FROM raw_vmware_vm_perf_agg
    WHERE instance = '' OR instance = '*'  -- Only aggregate metrics (no per-device breakdown)
    GROUP BY 
        collection_timestamp,
        vcenter_uuid,
        vm_moid,
        window_start,
        window_end,
        window_duration_seconds
)
SELECT 
    p.collection_timestamp,
    p.vcenter_uuid,
    p.vm_moid,
    p.window_start,
    p.window_end,
    p.window_duration_seconds,
    p.max_sample_count,
    
    -- CPU Metrics
    p.cpu_usage_avg_mhz,
    p.cpu_usage_min_mhz,
    p.cpu_usage_max_mhz,
    p.cpu_usagemhz_avg,
    p.cpu_ready_avg_ms,
    p.cpu_ready_max_ms,
    
    -- Memory Metrics
    ROUND(p.mem_usage_avg_percent::numeric, 2) AS mem_usage_avg_percent,
    ROUND(p.mem_usage_min_percent::numeric, 2) AS mem_usage_min_percent,
    ROUND(p.mem_usage_max_percent::numeric, 2) AS mem_usage_max_percent,
    ROUND((p.mem_consumed_avg_kb / 1024.0)::numeric, 2) AS mem_consumed_avg_mb,
    ROUND((p.mem_consumed_max_kb / 1024.0)::numeric, 2) AS mem_consumed_max_mb,
    ROUND((p.mem_active_avg_kb / 1024.0)::numeric, 2) AS mem_active_avg_mb,
    ROUND((p.mem_swapped_avg_kb / 1024.0)::numeric, 2) AS mem_swapped_avg_mb,
    ROUND((p.mem_balloon_avg_kb / 1024.0)::numeric, 2) AS mem_balloon_avg_mb,
    
    -- Disk I/O Metrics
    ROUND(p.disk_usage_avg_kbps::numeric, 2) AS disk_usage_avg_kbps,
    ROUND(p.disk_usage_max_kbps::numeric, 2) AS disk_usage_max_kbps,
    ROUND(p.disk_read_avg_kbps::numeric, 2) AS disk_read_avg_kbps,
    ROUND(p.disk_write_avg_kbps::numeric, 2) AS disk_write_avg_kbps,
    ROUND(((p.disk_read_avg_kbps + p.disk_write_avg_kbps) / 1024.0)::numeric, 2) AS disk_total_avg_mbps,
    
    -- Disk Latency
    ROUND(p.disk_read_latency_avg_ms::numeric, 2) AS disk_read_latency_avg_ms,
    ROUND(p.disk_read_latency_max_ms::numeric, 2) AS disk_read_latency_max_ms,
    ROUND(p.disk_write_latency_avg_ms::numeric, 2) AS disk_write_latency_avg_ms,
    ROUND(p.disk_write_latency_max_ms::numeric, 2) AS disk_write_latency_max_ms,
    
    -- Network Metrics
    ROUND(p.net_usage_avg_kbps::numeric, 2) AS net_usage_avg_kbps,
    ROUND(p.net_tx_avg_kbps::numeric, 2) AS net_tx_avg_kbps,
    ROUND(p.net_rx_avg_kbps::numeric, 2) AS net_rx_avg_kbps,
    ROUND(((p.net_tx_avg_kbps + p.net_rx_avg_kbps) / 1024.0)::numeric, 2) AS net_total_avg_mbps,
    ROUND(p.net_packets_rx_avg::numeric, 0) AS net_packets_rx_avg,
    ROUND(p.net_packets_tx_avg::numeric, 0) AS net_packets_tx_avg,
    
    -- Datastore Metrics
    ROUND(p.datastore_read_avg_kbps::numeric, 2) AS datastore_read_avg_kbps,
    ROUND(p.datastore_write_avg_kbps::numeric, 2) AS datastore_write_avg_kbps,
    ROUND(p.datastore_read_iops_avg::numeric, 0) AS datastore_read_iops_avg,
    ROUND(p.datastore_write_iops_avg::numeric, 0) AS datastore_write_iops_avg

FROM pivoted_metrics p;

-- Example Usage:
-- SELECT * FROM vmware_vm_metrics WHERE vm_moid = 'vm-12345' ORDER BY collection_timestamp DESC LIMIT 10;
-- SELECT vm_moid, cpu_usage_avg_mhz, mem_usage_avg_percent, disk_usage_avg_kbps, net_usage_avg_kbps FROM vmware_vm_metrics WHERE collection_timestamp > NOW() - INTERVAL '1 hour';

-- Combined View with Inventory
-- SELECT i.vm_name, i.power_state, m.cpu_usage_avg_mhz, m.mem_usage_avg_percent 
-- FROM vmware_vm_inventory i 
-- JOIN vmware_vm_metrics m ON i.vm_moid = m.vm_moid AND i.collection_timestamp = m.collection_timestamp
-- WHERE i.power_state = 'poweredOn' ORDER BY m.cpu_usage_avg_mhz DESC LIMIT 10;
