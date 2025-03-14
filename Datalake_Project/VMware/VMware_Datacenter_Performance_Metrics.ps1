######################## VmWare Credentials/Configurations ########################
# Define the path to the config file
$configFile = "/Datalake_Project/configuration_file.json"

# Check if the config file exists
if (-Not (Test-Path $configFile)) {
    Write-Host "Error: Configuration file not found!"
    exit 1
}

# Load the JSON file
$config = Get-Content $configFile | ConvertFrom-Json

# Access VMware values inside the "VmWare" section
$VMwareIP = $config.VmWare.VMwareIP
$VMwarePort = $config.VmWare.VMwarePort
$VMware_userName = $config.VmWare.VMware_userName
$VMware_password = $config.VmWare.VMware_password


$VMware_baseURL = "https://" + $VMwareIP
$contentType = "application/json"
#############################################################################################
######################## Disable SSL certificate checks ########################
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
Set-PowerCLIConfiguration -InvalidCertificateAction Ignore -Scope Session -Confirm:$false  | Out-Null
$progressPreference = "silentlyContinue"
#############################################################################################

######################## Authentication to base64 ########################
$authInfo = ("{0}:{1}" -f $VMware_userName, $VMware_password)
$authInfo = [System.Text.Encoding]::UTF8.GetBytes("$authInfo")
$authInfo = [System.Convert]::ToBase64String($authInfo)
#############################################################################################

######################## VMWARE AUTH TOKEN FUNCTION ########################
function getVmwareApiSession ($VMware_userName, $VMware_password){
  $xVMwareSessionURL = $VMware_baseURL +"/api/session"
  $headerS = @{ Authorization = "Basic $authInfo" }



  try {
    $VMwareSessionResponse = Invoke-WebRequest -Uri $xVMwareSessionURL -Headers $headerS -Method POST -ContentType $contentType -SkipCertificateCheck
    $content = $VMwareSessionResponse.content
    return $content.Substring(1, $content.Length - 2)
  }
  catch {
    Write-Host "Failed to retrieve VMware session: $($_.Exception.Message)"
    return $null
  }
}

$xVMwareSession = getVmwareApiSession $VMware_userName $VMware_password
########################################################################################

######################## VMWARE POWERCLI CONNECT ########################
$serverConnection = Connect-VIServer -Server $VMwareIP -Protocol https -User $VMware_userName -Password $VMware_password
########################################################################################

######################## VMWARE HEADER ########################
$headers = @{
    "vmware-api-session-id" = $xVMwareSession
    "Authorization" = "Basic " + $authInfo
}
########################################################################################
$now = Get-Date
$roundedMinutes = [math]::Floor($now.Minute / 15) * 15
$roundedTime = $now.Date.AddHours($now.Hour).AddMinutes($roundedMinutes)

# Set start time to 20 minutes before the nearest 15-minute mark
$startDate = $roundedTime.AddMinutes(-15)
$endDate = $roundedTime  # End time is the current time
$intervalMins = 15  # Interval set to 15 minutes

# Initialize an empty array for final results
$output = @()

# Retrieve all datacenters
$DatacenterTable = Get-Datacenter

foreach ($Datacenter in $DatacenterTable) {
    # Initialize counters for the datacenter level
    $totalMemoryCapacityGB = 0
    $totalMemoryUsedGB = 0
    $totalStorage = 0
    $usedStorage = 0
    $totalCpuCapacityGHz = 0
    $totalCpuUsedGHz = 0
    $totalDiskUsageKBpsAvg = 0
    $totalDiskUsageKBpsMin = 0
    $totalDiskUsageKBpsMax = 0
    $totalNetworkUsageKBpsAvg = 0
    $totalNetworkUsageKBpsMin = 0
    $totalNetworkUsageKBpsMax = 0
    $totalMemoryUsageAvg = 0
    $totalMemoryUsageMin = 0
    $totalMemoryUsageMax = 0
    $totalCpuUsageAvg = 0
    $totalCpuUsageMin = 0
    $totalCpuUsageMax = 0
    $totalHostCount = 0
    $totalVMCount = 0
    $totalClusterCount = 0

    # Get clusters, hosts, and VMs within the datacenter
    $clusters = Get-Cluster -Location $Datacenter
    $totalClusterCount = $clusters.Count
    $VMHosts = Get-VMHost -Location $Datacenter
    $totalHostCount = $VMHosts.Count
    $VMs = Get-VM -Location $Datacenter
    $totalVMCount = $VMs.Count

    # Calculate total memory, CPU, and disk usage across all clusters and hosts in the datacenter
        #######
    $datastores = Get-Datastore 
    foreach ($datastore in $datastores) {
            $totalStorage += $datastore.CapacityMB   # Convert from MB to GB
            $usedStorage += ($datastore.CapacityMB - $datastore.FreeSpaceMB)   # Convert used space from MB to GB
        }
        #####


    

    # Calculate total CPU, Memory, Disk, and Network usage across all hosts
    foreach ($VMHost in $VMHosts) {
        # CPU and Memory details
        $totalCpuCapacityGHz += [math]::Round($VMHost.CpuTotalMhz / 1000, 2)
        $totalCpuUsedGHz += [math]::Round($VMHost.CpuUsageMhz / 1000, 2)
        $totalMemoryCapacityGB += [math]::Round($VMHost.MemoryTotalGB, 2)
        $totalMemoryUsedGB += [math]::Round($VMHost.MemoryUsageGB, 2)

        # Disk, Network, Memory, and CPU statistics for the interval
        $diskStats = Get-Stat -Entity $VMHost -Stat disk.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
        $networkStats = Get-Stat -Entity $VMHost -Stat net.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
        $memoryStats = Get-Stat -Entity $VMHost -Stat mem.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
        $cpuStats = Get-Stat -Entity $VMHost -Stat cpu.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins

        # Aggregate Disk, Network, Memory, and CPU stats (Average, Min, Max)
        $totalDiskUsageKBpsAvg += if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
        $totalDiskUsageKBpsMin += if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
        $totalDiskUsageKBpsMax += if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

        $totalNetworkUsageKBpsAvg += if ($networkStats) { [Math]::Round(($networkStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
        $totalNetworkUsageKBpsMin += if ($networkStats) { [Math]::Round(($networkStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
        $totalNetworkUsageKBpsMax += if ($networkStats) { [Math]::Round(($networkStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

        $totalMemoryUsageAvg += if ($memoryStats) { [Math]::Round(($memoryStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
        $totalMemoryUsageMin += if ($memoryStats) { [Math]::Round(($memoryStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
        $totalMemoryUsageMax += if ($memoryStats) { [Math]::Round(($memoryStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

        $totalCpuUsageAvg += if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
        $totalCpuUsageMin += if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
        $totalCpuUsageMax += if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }
    }

        # Add data for the interval to the output
    $output += [PSCustomObject]@{
        datacenter                  = $Datacenter.Name
        timestamp                   = $startDate.ToString("yyyy-MM-dd HH:mm")
        total_memory_capacity_gb    = $totalMemoryCapacityGB
        total_memory_used_gb        = $totalMemoryUsedGB
        total_storage_capacity_gb   = $totalStorage
        total_used_storage_gb       = $usedStorage
        total_cpu_ghz_capacity      = $totalCpuCapacityGHz
        total_cpu_ghz_used          = $totalCpuUsedGHz
        disk_usage_avg_kbps         = $totalDiskUsageKBpsAvg
        disk_usage_min_kbps         = $totalDiskUsageKBpsMin
        disk_usage_max_kbps         = $totalDiskUsageKBpsMax
        network_usage_avg_kbps      = $totalNetworkUsageKBpsAvg
        network_usage_min_kbps      = $totalNetworkUsageKBpsMin
        network_usage_max_kbps      = $totalNetworkUsageKBpsMax
        memory_usage_avg_perc       = $totalMemoryUsageAvg/$totalHostCount
        memory_usage_min_perc       = $totalMemoryUsageMin/$totalHostCount
        memory_usage_max_perc       = $totalMemoryUsageMax/$totalHostCount
        cpu_usage_avg_perc          = $totalCpuUsageAvg/$totalHostCount
        cpu_usage_min_perc          = $totalCpuUsageMin/$totalHostCount
        cpu_usage_max_perc          = $totalCpuUsageMax/$totalHostCount
        total_host_count            = $totalHostCount
        total_vm_count              = $totalVMCount
        total_cluster_count         = $totalClusterCount
}
}

# Output formatted results to a text file and the console
$output | ForEach-Object {
    "datacenter: $($_.datacenter)"
    "timestamp: $($_.timestamp)"
    "total memory capacity gb: $($_.total_memory_capacity_gb)"
    "total memory used gb: $($_.total_memory_used_gb)"
    "total storage capacity gb: $($_.total_storage_capacity_gb)"
    "total used storage gb: $($_.total_used_storage_gb)"
    "total cpu ghz capacity: $($_.total_cpu_ghz_capacity)"
    "total cpu ghz used: $($_.total_cpu_ghz_used)"
    "disk usage avg kbps: $($_.disk_usage_avg_kbps)"
    "disk usage min kbps: $($_.disk_usage_min_kbps)"
    "disk usage max kbps: $($_.disk_usage_max_kbps)"
    "network usage avg kbps: $($_.network_usage_avg_kbps)"
    "network usage min kbps: $($_.network_usage_min_kbps)"
    "network usage max kbps: $($_.network_usage_max_kbps)"
    "memory usage avg perc: $($_.memory_usage_avg_perc)"
    "memory usage min perc: $($_.memory_usage_min_perc)"
    "memory usage max perc: $($_.memory_usage_max_perc)"
    "cpu usage avg perc: $($_.cpu_usage_avg_perc)"
    "cpu usage min perc: $($_.cpu_usage_min_perc)"
    "cpu usage max perc: $($_.cpu_usage_max_perc)"
    "total host count: $($_.total_host_count)"
    "total vm count: $($_.total_vm_count)"
    "total cluster count: $($_.total_cluster_count)"
    
    ""
} | Tee-Object -FilePath "/Datalake_Project/datacenter_summary.txt" -Encoding utf8
