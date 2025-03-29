# VMware Datacenter Performance Metrics Script - Güncel Versiyon

# JSON konfigürasyon dosyasının yolu
$configFilePath = "/Datalake_Project/configuration_file.json"

# Konfigürasyon dosyasını oku ve nesneye dönüştür
$config = Get-Content $configFilePath | ConvertFrom-Json

# VmWare konfigürasyon değerlerini al
$vmwareIpString = $config.VmWare.VMwareIP
$VMwarePort = $config.VmWare.VMwarePort
$VMware_userName = $config.VmWare.VMware_userName
$VMware_password = $config.VmWare.VMware_password

# Eğer değer boş değilse, virgül ile böl ve temizle; boşsa boş array oluştur
if ($vmwareIpString -ne "") {
    $vmwareIps = $vmwareIpString -split "," | ForEach-Object { $_.Trim() }
} else {
    $vmwareIps = @()
}

# Her bir IP adresi için işlemleri gerçekleştir ve çıktıyı ver
foreach ($ip in $vmwareIps) {
    
    
    # Burada her bir IP için gerçekleştirmek istediğiniz işlemleri ekleyin.
    # Kodun içerisinde bulunan $VMwareIP değerini $ip değeri ile değiştirin    
    
}

# Diğer script kısımlarınız varsa, burada devam edebilirsiniz.
