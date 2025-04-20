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

if ($VMwareIP -ne "") {
    $vmwareIps = $VMwareIP -split "," | ForEach-Object { $_.Trim() }
} else {
    $vmwareIps = @()
}

# Her bir IP adresi için işlemleri gerçekleştir ve çıktıyı ver
foreach ($ip in $vmwareIps) {
    $VMware_baseURL = "https://" + $ip
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
        # Write-Host "Failed to retrieve VMware session: $($_.Exception.Message)"
        return $null
    }
    }

    $xVMwareSession = getVmwareApiSession $VMware_userName $VMware_password
    ########################################################################################

    ######################## VMWARE POWERCLI CONNECT ########################
    $serverConnection = Connect-VIServer -Server $ip -Protocol https -User $VMware_userName -Password $VMware_password
    ########################################################################################

    ######################## VMWARE HEADER ########################
    $headers = @{
        "vmware-api-session-id" = $xVMwareSession
        "Authorization" = "Basic " + $authInfo
    }
    ########################################################################################
    # Get the list of datacenters
    # Define date range and interval for stats
    $output = @()

    # Get the current date and time and round it to the nearest past 15-minute interval
    $now = Get-Date
    $roundedMinutes = [math]::Floor($now.Minute / 15) * 15
    $roundedTime = $now.Date.AddHours($now.Hour).AddMinutes($roundedMinutes)

    # Set start time to 20 minutes before the nearest 15-minute mark
    $startDate = $roundedTime.AddMinutes(-15)
    $endDate = $roundedTime  # End time is the current time
    $intervalMins = 15  # Interval set to 15 minutes

    # Retrieve all datacenters
    $DatacenterTable = Get-Datacenter

    # Loop through each datacenter
    foreach ($Datacenter in $DatacenterTable) {
        # Get all VMHosts in the datacenter
        $VMHosts = Get-VMHost -Location $Datacenter

        # Process each VMHost
        foreach ($VMHost in $VMHosts) {
            # Host UUIDs
            $hostUUID = $VMHost.Extensiondata.Hardware.SystemInfo.Uuid
            $hostSystemUUID = try {
                $esxcli = Get-EsxCli -VMHost $VMHost -V2
                $esxcli.hardware.platform.get.Invoke().Uuid
            } catch {
                $null # In case Get-Esxcli fails, assign null
            }
            $uptimeSeconds = $VMHost.ExtensionData.Runtime.BootTime

            # Disk, Network, Memory, and CPU statistics for the specified interval
            $diskStats = Get-Stat -Entity $VMHost -Stat disk.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
            $networkStats = Get-Stat -Entity $VMHost -Stat net.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
            $memoryStats = Get-Stat -Entity $VMHost -Stat mem.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
            $cpuStats = Get-Stat -Entity $VMHost -Stat cpu.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
            
            $powerUsage = Get-Stat -Entity $VMHost -Stat power.power.average -Realtime -MaxSamples 1

            # Calculate min, max, and average for Disk, Network, Memory, and CPU stats
            $diskUsageAvg = if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
            $diskUsageMin = if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
            $diskUsageMax = if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

            $networkUsageAvg = if ($networkStats) { [Math]::Round(($networkStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
            $networkUsageMin = if ($networkStats) { [Math]::Round(($networkStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
            $networkUsageMax = if ($networkStats) { [Math]::Round(($networkStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

            $memoryUsageAvg = if ($memoryStats) { [Math]::Round(($memoryStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
            $memoryUsageMin = if ($memoryStats) { [Math]::Round(($memoryStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
            $memoryUsageMax = if ($memoryStats) { [Math]::Round(($memoryStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

            $cpuUsageAvg = if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
            $cpuUsageMin = if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
            $cpuUsageMax = if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

            # Retrieve Datastore information for each VMHost with specific fields
            $datastores = Get-Datastore -RelatedObject $VMHost
            $totalFreeSpaceGB = [math]::Round(($datastores | Measure-Object -Property FreeSpaceMB -Sum).Sum / 1024, 2)  # Convert MB to GB
            $totalCapacityGB = [math]::Round(($datastores | Measure-Object -Property CapacityMB -Sum).Sum / 1024, 2)   # Convert MB to GB

            # CPU and Memory details
            $cpuCapacityGHz = [math]::Round($VMHost.CpuTotalMhz / 1000, 2)
            $cpuUsedGHz = [math]::Round($VMHost.CpuUsageMhz / 1000, 2)
            $cpuFreeGHz = [math]::Round(($VMHost.CpuTotalMhz - $VMHost.CpuUsageMhz) / 1000, 2)
            $memoryCapacityGB = [math]::Round($VMHost.MemoryTotalGB, 2)
            $memoryUsedGB = [math]::Round($VMHost.MemoryUsageGB, 2)
            $memoryFreeGB = [math]::Round(($VMHost.MemoryTotalGB - $VMHost.MemoryUsageGB), 2)

            # Create custom object for each interval and add to output
            $output += [PSCustomObject]@{
                Datacenter                    = $Datacenter.Name
                Cluster                       = (Get-Cluster -VMHost $VMHost).Name
                VMHost                        = $VMHost.Name
                Timestamp                     = $startDate.ToString("yyyy-MM-dd HH:mm")
                "ESXi System UUID"            = $hostUUID
                "ESXi BIOS UUID"              = $hostSystemUUID
                "CPU GHz Capacity"            = $cpuCapacityGHz
                "CPU GHz Used"                = $cpuUsedGHz
                "CPU GHz Free"                = $cpuFreeGHz
                "Memory Capacity GB"          = $memoryCapacityGB
                "Memory Used GB"              = $memoryUsedGB
                "Memory Free GB"              = $memoryFreeGB
                "Disk Usage Average, KBps"    = $diskUsageAvg
                "Disk Usage Minimum, KBps"    = $diskUsageMin
                "Disk Usage Maximum, KBps"    = $diskUsageMax
                "Network Usage Average, KBps" = $networkUsageAvg
                "Network Usage Minimum, KBps" = $networkUsageMin
                "Network Usage Maximum, KBps" = $networkUsageMax
                "Memory Usage Average, perc"     = $memoryUsageAvg
                "Memory Usage Minimum, perc"     = $memoryUsageMin
                "Memory Usage Maximum, perc"     = $memoryUsageMax
                "CPU Usage Average, perc"        = $cpuUsageAvg
                "CPU Usage Minimum, perc"        = $cpuUsageMin
                "CPU Usage Maximum, perc"        = $cpuUsageMax
                TotalFreeSpaceGB              = $totalFreeSpaceGB
                TotalCapacityGB               = $totalCapacityGB
                "Power Usage"                     = $powerUsage
                "Uptime"                        =$uptimeSeconds
            }
        }
    }

    # Output formatted results to a text file and the console
    $output | ForEach-Object {
        "Datacenter: $($_.Datacenter)"
        "Cluster: $($_.Cluster)"
        "VMHost: $($_.VMHost)"
        "Timestamp: $($_.Timestamp)"
        "ESXi System UUID: $($_.'ESXi System UUID')"
        "ESXi BIOS UUID: $($_.'ESXi BIOS UUID')"
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
        "Total FreeSpaceGB: $($_.TotalFreeSpaceGB)"
        "Total CapacityGB: $($_.TotalCapacityGB)"
        "Power Usage: $($_.'Power Usage')"
        "Uptime: $($_.'Uptime')"
        ""
    } #| Tee-Object -FilePath "/nifiScripts/output9.txt" -Encoding utf8

}