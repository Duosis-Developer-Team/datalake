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
# Get the list of datacenters
# Define date range and interval for stats
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
    # Get all clusters within the datacenter
    $clusters = Get-Cluster -Location $Datacenter
    
    foreach ($cluster in $clusters) {
        # Get all VMHosts in the cluster
        $VMHosts = Get-VMHost -Location $cluster
        $vHostCount = $VMHosts.Count
        $vmCount = (Get-VM -Location $cluster).Count

        # Calculate total storage and used storage for the cluster's datastores
        $datastores = Get-Cluster -Name $cluster.Name | Get-Datastore
        $totalStorage = [math]::Round(($datastores | Measure-Object -Property CapacityMB -Sum).Sum / 1024, 2)  # Convert MB to GB
        $usedStorage = [math]::Round(($datastores | Measure-Object -Property FreeSpaceMB -Sum).Sum / 1024, 2)  # Convert used space from MB to GB

        # Initialize totals for the current interval
        $totalCpuCapacityGHz = 0
        $totalCpuUsedGHz = 0
        $totalCpuFreeGHz = 0
        $totalMemoryCapacityGB = 0
        $totalMemoryUsedGB = 0
        $totalMemoryFreeGB = 0
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

        # Process each VMHost in the cluster for the current interval
        foreach ($VMHost in $VMHosts) {
            # Retrieve host-level information and aggregate it for the cluster
            $cpuCapacityGHz = [math]::Round($VMHost.CpuTotalMhz / 1000, 2)
            $cpuUsedGHz = [math]::Round($VMHost.CpuUsageMhz / 1000, 2)
            $cpuFreeGHz = $cpuCapacityGHz - $cpuUsedGHz
            $memoryCapacityGB = [math]::Round($VMHost.MemoryTotalGB, 2)
            $memoryUsedGB = [math]::Round($VMHost.MemoryUsageGB, 2)
            $memoryFreeGB = $memoryCapacityGB - $memoryUsedGB

            # Accumulate CPU and Memory capacities
            $totalCpuCapacityGHz += $cpuCapacityGHz
            $totalCpuUsedGHz += $cpuUsedGHz
            $totalCpuFreeGHz += $cpuFreeGHz
            $totalMemoryCapacityGB += $memoryCapacityGB
            $totalMemoryUsedGB += $memoryUsedGB
            $totalMemoryFreeGB += $memoryFreeGB

            # Collect and aggregate Disk, Network, Memory, and CPU stats for the interval
            $diskStats = Get-Stat -Entity $VMHost -Stat disk.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
            $networkStats = Get-Stat -Entity $VMHost -Stat net.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
            $memoryStats = Get-Stat -Entity $VMHost -Stat mem.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
            $cpuStats = Get-Stat -Entity $VMHost -Stat cpu.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins

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

        # Add data for the cluster at the current interval
        $output += [PSCustomObject]@{
            Datacenter                    = $Datacenter.Name
            Cluster                       = $cluster.Name
            Timestamp                     = $startDate.ToString("yyyy-MM-dd HH:mm")
            "vHost Count"                 = $vHostCount
            "VM Count"                    = $vmCount
            "CPU GHz Capacity"            = $totalCpuCapacityGHz
            "CPU GHz Used"                = $totalCpuUsedGHz
            "CPU GHz Free"                = $totalCpuFreeGHz
            "Memory Capacity GB"          = $totalMemoryCapacityGB
            "Memory Used GB"              = $totalMemoryUsedGB
            "Memory Free GB"              = $totalMemoryFreeGB
            "Disk Usage Average, KBps"    = $totalDiskUsageKBpsAvg
            "Disk Usage Minimum, KBps"    = $totalDiskUsageKBpsMin
            "Disk Usage Maximum, KBps"    = $totalDiskUsageKBpsMax
            "Network Usage Average, KBps" = $totalNetworkUsageKBpsAvg
            "Network Usage Minimum, KBps" = $totalNetworkUsageKBpsMin
            "Network Usage Maximum, KBps" = $totalNetworkUsageKBpsMax
            "Memory Usage Average, perc"     = $totalMemoryUsageAvg/$vHostCount
            "Memory Usage Minimum, perc"     = $totalMemoryUsageMin/$vHostCount
            "Memory Usage Maximum, perc"     = $totalMemoryUsageMax/$vHostCount
            "CPU Usage Average, perc"        = $totalCpuUsageAvg/$vHostCount
            "CPU Usage Minimum, perc"        = $totalCpuUsageMin/$vHostCount
            "CPU Usage Maximum, perc"        = $totalCpuUsageMax/$vHostCount
            TotalFreeSpaceGB              = $usedStorage
            TotalCapacityGB               = $totalStorage
        }
    }
}

# Output formatted results to a text file and the console
$output | ForEach-Object {
    "Datacenter: $($_.Datacenter)"
    "Cluster: $($_.Cluster)"
    "Timestamp: $($_.Timestamp)"
    "vHost Count: $($_.'vHost Count')"
    "VM Count: $($_.'VM Count')"
    "CPU GHz Capacity: $($_.'CPU GHz Capacity')"
    "CPU GHz Used: $($_.'CPU GHz Used')"
    "CPU GHz Free: $($_.'CPU GHz Free')"
    "Memory Capacity GB: $($_.'Memory Capacity GB')"
    "Memory Used GB: $($_.'Memory Used GB')"
    "Memory Free GB: $($_.'Memory Free GB')"
    "Disk Usage Avg KBps: $($_.'Disk Usage Average, KBps')"
    "Disk Usage Min KBps: $($_.'Disk Usage Minimum, KBps')"
    "Disk Usage Max KBps: $($_.'Disk Usage Maximum, KBps')"
    "Network Usage Avg KBps: $($_.'Network Usage Average, KBps')"
    "Network Usage Min KBps: $($_.'Network Usage Minimum, KBps')"
    "Network Usage Max KBps: $($_.'Network Usage Maximum, KBps')"
    "Memory Usage Avg perc: $($_.'Memory Usage Average, perc')"
    "Memory Usage Min perc: $($_.'Memory Usage Minimum, perc')"
    "Memory Usage Max perc: $($_.'Memory Usage Maximum, perc')"
    "CPU Usage Avg perc: $($_.'CPU Usage Average, perc')"
    "CPU Usage Min perc: $($_.'CPU Usage Minimum, perc')"
    "CPU Usage Max perc: $($_.'CPU Usage Maximum, perc')"
    "Total FreeSpace GB: $($_.TotalFreeSpaceGB)"
    "Total Capacity GB: $($_.TotalCapacityGB)"
    ""
} | Tee-Object -FilePath "/nifiScripts/cluster_summary_15min_intervals.txt" -Encoding utf8