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
# Get the list of datacenters
# Define date range and interval for stats
# Set start and end dates for one day (last 24 hours)

# Get the current date and time
# Get the current date and time, rounded down to the nearest 15-minute interval
$output = @()

# Get the current date and time and round it to the nearest past 15-minute interval
$now = Get-Date
$roundedMinutes = [math]::Floor($now.Minute / 15) * 15
$roundedTime = $now.Date.AddHours($now.Hour).AddMinutes($roundedMinutes)

# Set start time to 20 minutes before the nearest 15-minute mark
$startDate = $roundedTime.AddMinutes(-15)
$endDate = $roundedTime  # End time is the current time
$intervalMins = 15  # Interval set to 15 minutes

# Retrieve all datacenters and iterate through each datacenter's powered-on VMs
$DatacenterTable = Get-Datacenter
foreach ($Datacenter in $DatacenterTable) {
    # Get all powered-on VMs in the datacenter
    $poweredOnVMs = Get-VM -Location $Datacenter | Where-Object { $_.PowerState -eq "PoweredOn" }
    $totalCPUs = 0
    $totalMemoryGB = 0
    # Process each powered-on VM
    foreach ($VM in $poweredOnVMs) {
        # Retrieve 15-minute statistics at the specified time
        $cpuStats = Get-Stat -Entity $VM -Stat cpu.usagemhz.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
        $memStats = Get-Stat -Entity $VM -Stat mem.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins
        $diskStats = Get-Stat -Entity $VM -Stat disk.usage.average -Start $startDate -Finish $endDate -IntervalMins $intervalMins

        # Calculate averages, minimums, and maximums for CPU, Memory, and Disk usage
        $cpuUsageAvg = if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
        $cpuUsageMin = if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
        $cpuUsageMax = if ($cpuStats) { [Math]::Round(($cpuStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

        $memUsageAvg = if ($memStats) { [Math]::Round(($memStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
        $memUsageMin = if ($memStats) { [Math]::Round(($memStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
        $memUsageMax = if ($memStats) { [Math]::Round(($memStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

        $diskUsageAvg = if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Average).Average, 2) } else { 0 }
        $diskUsageMin = if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Minimum).Minimum, 2) } else { 0 }
        $diskUsageMax = if ($diskStats) { [Math]::Round(($diskStats | Measure-Object -Property Value -Maximum).Maximum, 2) } else { 0 }

        # Get VM host and cluster information
        $VMHost = Get-VMHost -VM $VM
        $hostUUID = $VMHost.Extensiondata.Hardware.SystemInfo.Uuid
        $Cluster = Get-Cluster -VMHost $VMHost
        $VMHostName = $VMHost.Name
        $ClusterName = $Cluster.Name

        # Get additional VM properties
        $NumCpu = $VM.NumCpu
        $CPUSocket = $VM.Config.Hardware.NumCPU
        $cpuCapacityMhz = $VM.ExtensionData.ResourceConfig.CpuAllocation.Reservation
        $memoryCapacityGB = [Math]::Round($VM.MemoryGB, 2) 

        # Retrieve Datastore names and UUID for the VM
        $datastores = [string]::Join(',', (Get-Datastore -Id $VM.DatastoreIdList | Select-Object -ExpandProperty Name))
        $uuid = (Get-View $VM.Id).Config.Uuid
        $vmid_vmuuid = "$($VM.Id):$uuid"

        $VMView = $VM | Get-View
        $BootTime = $VMView.Runtime.BootTime
        # Add the VM's information and 15-minute statistics to results array
        $output += [PSCustomObject]@{
            "Datacenter"               = $Datacenter.Name
            "Cluster"                  = $ClusterName
            "VMHost"                   = $VMHostName
            "VMName"                   = $VM.Name
            "Timestamp"                = $endDate.ToString("yyyy-MM-dd HH:mm")
            "CPU Socket"               = $CPUSocket
            "Number of CPUs"           = $NumCpu
            "ESXi System UUID"         = $hostUUID
            "CPU Usage Average, Mhz"   = $cpuUsageAvg
            "CPU Usage Minimum, Mhz"   = $cpuUsageMin
            "CPU Usage Maximum, Mhz"   = $cpuUsageMax
            "Memory Usage Average, perc"  = $memUsageAvg
            "Memory Usage Minimum, perc"  = $memUsageMin
            "Memory Usage Maximum, perc"  = $memUsageMax
            "Disk Usage Average, KBps" = $diskUsageAvg
            "Disk Usage Minimum, KBps" = $diskUsageMin
            "Disk Usage Maximum, KBps" = $diskUsageMax
            "Total CPU Capacity, Mhz"   = $cpuCapacityMhz
            "Total Memory Capacity, GB" = $memoryCapacityGB
            "GuestOS"                  = $VM.ExtensionData.Guest.GuestFullName
            "Datastore"                = $datastores
            "UsedSpaceGB"              = [Math]::Round($VM.UsedSpaceGB, 1)
            "ProvisionedSpaceGB"       = [Math]::Round($VM.ProvisionedSpaceGB, 1)
            "Folder"                   = $VM.Folder.Name
            "UUID"                     = $vmid_vmuuid
            "BootTime"                  = $BootTime
        }
    }
}
# Output the results to file
$output | ForEach-Object {
    "Datacenter: $($_.Datacenter)"
    "Cluster: $($_.Cluster)"
    "VMHost: $($_.VMHost)"
    "VMName: $($_.VMName)"
    "Timestamp: $($_.Timestamp)"
    "Number of CPUs: $($_.'Number of CPUs')"
    "ESXi System UUID: $($_.'ESXi System UUID')"
    "Total CPU Capacity Mhz: $($_.'Total CPU Capacity, Mhz')"
    "Total Memory Capacity GB: $($_.'Total Memory Capacity, GB')"
    "CPU Usage Avg Mhz: $($_.'CPU Usage Average, Mhz')"
    "CPU Usage Min Mhz: $($_.'CPU Usage Minimum, Mhz')"
    "CPU Usage Max Mhz: $($_.'CPU Usage Maximum, Mhz')"
    "Memory Usage Avg perc: $($_.'Memory Usage Average, perc')"
    "Memory Usage Min perc: $($_.'Memory Usage Minimum, perc')"
    "Memory Usage Max perc: $($_.'Memory Usage Maximum, perc')"
    "Disk Usage Avg KBps: $($_.'Disk Usage Average, KBps')"
    "Disk Usage Min KBps: $($_.'Disk Usage Minimum, KBps')"
    "Disk Usage Max KBps: $($_.'Disk Usage Maximum, KBps')"
    "Guest OS: $($_.GuestOS)"
    "Datastore: $($_.Datastore)"
    "Used Space GB: $($_.UsedSpaceGB)"
    "Provisioned Space GB: $($_.'ProvisionedSpaceGB')"
    "Folder: $($_.Folder)"
    "UUID: $($_.UUID)"
    "BootTime: $($_.BootTime)"
    ""
} | Tee-Object -FilePath "/Datalake_Project/vm15MinSummary.txt" -Encoding utf8

