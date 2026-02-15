-- VMware Host Performance Metrics View
-- Pivots aggregated performance metrics from raw_vmware_host_perf_agg
-- Purpose: Easy access to common performance metrics per host and timestamp

CREATE OR REPLACE VIEW vmware_host_metrics AS
WITH pivoted AS (
    SELECT
        collection_timestamp,
        vcenter_uuid,
        host_moid,
        
        -- CPU Metrics (MHz)
        MAX(CASE WHEN counter_name = 'cpu.usage.average' THEN value_avg END) AS cpu_usage_avg_mhz,
        MAX(CASE WHEN counter_name = 'cpu.usage.average' THEN value_min END) AS cpu_usage_min_mhz,
        MAX(CASE WHEN counter_name = 'cpu.usage.average' THEN value_max END) AS cpu_usage_max_mhz,
        MAX(CASE WHEN counter_name = 'cpu.usagemhz.average' THEN value_avg END) AS cpu_usagemhz_avg,
        MAX(CASE WHEN counter_name = 'cpu.utilization.average' THEN value_avg END) AS cpu_utilization_avg_percent,
        MAX(CASE WHEN counter_name = 'cpu.coreUtilization.average' THEN value_avg END) AS cpu_core_util_avg_percent,
        MAX(CASE WHEN counter_name = 'cpu.ready.summation' THEN value_avg END) AS cpu_ready_avg_ms,
        MAX(CASE WHEN counter_name = 'cpu.costop.summation' THEN value_avg END) AS cpu_costop_avg_ms,
        
        -- Memory Metrics (KB)
        MAX(CASE WHEN counter_name = 'mem.usage.average' THEN value_avg END) AS mem_usage_avg_percent,
        MAX(CASE WHEN counter_name = 'mem.usage.average' THEN value_min END) AS mem_usage_min_percent,
        MAX(CASE WHEN counter_name = 'mem.usage.average' THEN value_max END) AS mem_usage_max_percent,
        MAX(CASE WHEN counter_name = 'mem.consumed.average' THEN value_avg END) AS mem_consumed_avg_kb,
        MAX(CASE WHEN counter_name = 'mem.consumed.average' THEN value_max END) AS mem_consumed_max_kb,
        MAX(CASE WHEN counter_name = 'mem.active.average' THEN value_avg END) AS mem_active_avg_kb,
        MAX(CASE WHEN counter_name = 'mem.swapused.average' THEN value_avg END) AS mem_swapused_avg_kb,
        MAX(CASE WHEN counter_name = 'mem.state.latest' THEN value_avg END) AS mem_state,
        
        -- Disk I/O Metrics (KBps and IOPS)
        MAX(CASE WHEN counter_name = 'disk.usage.average' THEN value_avg END) AS disk_usage_avg_kbps,
        MAX(CASE WHEN counter_name = 'disk.usage.average' THEN value_max END) AS disk_usage_max_kbps,
        MAX(CASE WHEN counter_name = 'disk.read.average' THEN value_avg END) AS disk_read_avg_kbps,
        MAX(CASE WHEN counter_name = 'disk.write.average' THEN value_avg END) AS disk_write_avg_kbps,
        MAX(CASE WHEN counter_name = 'disk.numberRead.summation' THEN value_avg END) AS disk_read_iops,
        MAX(CASE WHEN counter_name = 'disk.numberWrite.summation' THEN value_avg END) AS disk_write_iops,
        MAX(CASE WHEN counter_name = 'disk.deviceLatency.average' THEN value_avg END) AS disk_device_latency_avg_ms,
        MAX(CASE WHEN counter_name = 'disk.kernelLatency.average' THEN value_avg END) AS disk_kernel_latency_avg_ms,
        
        -- Network Metrics (KBps and Packets)
        MAX(CASE WHEN counter_name = 'net.usage.average' THEN value_avg END) AS net_usage_avg_kbps,
        MAX(CASE WHEN counter_name = 'net.usage.average' THEN value_max END) AS net_usage_max_kbps,
        MAX(CASE WHEN counter_name = 'net.received.average' THEN value_avg END) AS net_received_avg_kbps,
        MAX(CASE WHEN counter_name = 'net.transmitted.average' THEN value_avg END) AS net_transmitted_avg_kbps,
        MAX(CASE WHEN counter_name = 'net.packetsRx.summation' THEN value_avg END) AS net_packets_rx,
        MAX(CASE WHEN counter_name = 'net.packetsTx.summation' THEN value_avg END) AS net_packets_tx,
        MAX(CASE WHEN counter_name = 'net.droppedRx.summation' THEN value_avg END) AS net_dropped_rx,
        MAX(CASE WHEN counter_name = 'net.droppedTx.summation' THEN value_avg END) AS net_dropped_tx,
        
        -- Datastore Latency Metrics (ms)
        MAX(CASE WHEN counter_name = 'datastore.totalReadLatency.average' THEN value_avg END) AS datastore_read_latency_avg_ms,
        MAX(CASE WHEN counter_name = 'datastore.totalWriteLatency.average' THEN value_avg END) AS datastore_write_latency_avg_ms
        
    FROM raw_vmware_host_perf_agg
    WHERE data_type = 'vmware_host_perf_agg'
    GROUP BY collection_timestamp, vcenter_uuid, host_moid
)
SELECT 
    p.collection_timestamp,
    p.vcenter_uuid,
    p.host_moid,
    
    -- CPU Metrics (Raw values)
    ROUND(p.cpu_usage_avg_mhz::numeric, 2) AS cpu_usage_avg_mhz,
    ROUND(p.cpu_usage_min_mhz::numeric, 2) AS cpu_usage_min_mhz,
    ROUND(p.cpu_usage_max_mhz::numeric, 2) AS cpu_usage_max_mhz,
    ROUND(p.cpu_usagemhz_avg::numeric, 2) AS cpu_usagemhz_avg,
    ROUND(p.cpu_utilization_avg_percent::numeric, 2) AS cpu_utilization_avg_percent,
    ROUND(p.cpu_core_util_avg_percent::numeric, 2) AS cpu_core_util_avg_percent,
    ROUND(p.cpu_ready_avg_ms::numeric, 2) AS cpu_ready_avg_ms,
    ROUND(p.cpu_costop_avg_ms::numeric, 2) AS cpu_costop_avg_ms,
    
    -- CPU Metrics (Human Readable)
    ROUND((p.cpu_usage_avg_mhz / 1000.0)::numeric, 2) AS cpu_usage_avg_ghz,
    ROUND((p.cpu_usage_max_mhz / 1000.0)::numeric, 2) AS cpu_usage_max_ghz,
    
    -- Memory Metrics (Percentage)
    ROUND(p.mem_usage_avg_percent::numeric, 2) AS mem_usage_avg_percent,
    ROUND(p.mem_usage_min_percent::numeric, 2) AS mem_usage_min_percent,
    ROUND(p.mem_usage_max_percent::numeric, 2) AS mem_usage_max_percent,
    
    -- Memory Metrics (MB)
    ROUND((p.mem_consumed_avg_kb / 1024.0)::numeric, 2) AS mem_consumed_avg_mb,
    ROUND((p.mem_consumed_max_kb / 1024.0)::numeric, 2) AS mem_consumed_max_mb,
    ROUND((p.mem_active_avg_kb / 1024.0)::numeric, 2) AS mem_active_avg_mb,
    ROUND((p.mem_swapused_avg_kb / 1024.0)::numeric, 2) AS mem_swapused_avg_mb,
    
    -- Memory Metrics (GB)
    ROUND((p.mem_consumed_avg_kb / (1024.0^2))::numeric, 2) AS mem_consumed_avg_gb,
    ROUND((p.mem_active_avg_kb / (1024.0^2))::numeric, 2) AS mem_active_avg_gb,
    p.mem_state AS mem_state,
    
    -- Disk I/O Metrics (KBps)
    ROUND(p.disk_usage_avg_kbps::numeric, 2) AS disk_usage_avg_kbps,
    ROUND(p.disk_usage_max_kbps::numeric, 2) AS disk_usage_max_kbps,
    ROUND(p.disk_read_avg_kbps::numeric, 2) AS disk_read_avg_kbps,
    ROUND(p.disk_write_avg_kbps::numeric, 2) AS disk_write_avg_kbps,
    
    -- Disk I/O Metrics (MBps)
    ROUND((p.disk_usage_avg_kbps / 1024.0)::numeric, 2) AS disk_usage_avg_mbps,
    ROUND((p.disk_usage_max_kbps / 1024.0)::numeric, 2) AS disk_usage_max_mbps,
    ROUND((p.disk_read_avg_kbps / 1024.0)::numeric, 2) AS disk_read_avg_mbps,
    ROUND((p.disk_write_avg_kbps / 1024.0)::numeric, 2) AS disk_write_avg_mbps,
    
    -- Disk I/O Metrics (IOPS & Latency)
    ROUND(p.disk_read_iops::numeric, 2) AS disk_read_iops,
    ROUND(p.disk_write_iops::numeric, 2) AS disk_write_iops,
    ROUND(p.disk_device_latency_avg_ms::numeric, 2) AS disk_device_latency_avg_ms,
    ROUND(p.disk_kernel_latency_avg_ms::numeric, 2) AS disk_kernel_latency_avg_ms,
    ROUND((p.disk_device_latency_avg_ms + p.disk_kernel_latency_avg_ms)::numeric, 2) AS disk_total_latency_avg_ms,
    
    -- Network Metrics (KBps)
    ROUND(p.net_usage_avg_kbps::numeric, 2) AS net_usage_avg_kbps,
    ROUND(p.net_usage_max_kbps::numeric, 2) AS net_usage_max_kbps,
    ROUND(p.net_received_avg_kbps::numeric, 2) AS net_received_avg_kbps,
    ROUND(p.net_transmitted_avg_kbps::numeric, 2) AS net_transmitted_avg_kbps,
    
    -- Network Metrics (Mbps)
    ROUND((p.net_usage_avg_kbps * 8 / 1024.0)::numeric, 2) AS net_usage_avg_mbps,
    ROUND((p.net_usage_max_kbps * 8 / 1024.0)::numeric, 2) AS net_usage_max_mbps,
    ROUND((p.net_received_avg_kbps * 8 / 1024.0)::numeric, 2) AS net_received_avg_mbps,
    ROUND((p.net_transmitted_avg_kbps * 8 / 1024.0)::numeric, 2) AS net_transmitted_avg_mbps,
    
    -- Network Metrics (Packets)
    ROUND(p.net_packets_rx::numeric, 0) AS net_packets_rx,
    ROUND(p.net_packets_tx::numeric, 0) AS net_packets_tx,
    ROUND(p.net_dropped_rx::numeric, 0) AS net_dropped_rx,
    ROUND(p.net_dropped_tx::numeric, 0) AS net_dropped_tx,
    
    -- Datastore Latency
    ROUND(p.datastore_read_latency_avg_ms::numeric, 2) AS datastore_read_latency_avg_ms,
    ROUND(p.datastore_write_latency_avg_ms::numeric, 2) AS datastore_write_latency_avg_ms

FROM pivoted p;

-- Example Usage:
-- SELECT * FROM vmware_host_metrics WHERE host_moid = 'host-123' ORDER BY collection_timestamp DESC LIMIT 10;
-- SELECT host_moid, cpu_utilization_avg_percent, mem_usage_avg_percent, disk_usage_avg_mbps FROM vmware_host_metrics WHERE collection_timestamp > NOW() - INTERVAL '1 hour';
