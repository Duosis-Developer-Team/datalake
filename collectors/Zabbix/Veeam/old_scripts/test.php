<?php
require_once "ZabbixApi.php";
use IntelliTrend\Zabbix\ZabbixApi;
use IntelliTrend\Zabbix\ZabbixApiException;

$zbx = new ZabbixApi();

/* --------------------------------------------------------------------------
   1) Yapılandırma dosyasını oku
   -------------------------------------------------------------------------- */
$configPath = "/Datalake_Project/configuration_file.json";
$config     = json_decode(file_get_contents($configPath), true);

$zabUrl      = $config["Zabbix"]["zabUrl"];
$zabUser     = $config["Zabbix"]["zabUser"];
$zabPassword = $config["Zabbix"]["zabPassword"];

/* --------------------------------------------------------------------------
   2) Değişkenler
   -------------------------------------------------------------------------- */
$groupids   = ["1576"];           // gerekirse çoğaltın
$outputFile = __DIR__ . "/output.json";

header('Content-Type: text/plain; charset=utf-8');

try {
    // SSL doğrulaması devre dışı
    $zbx->login($zabUrl, $zabUser, $zabPassword,
                ['sslVerifyPeer' => false, 'sslVerifyHost' => false]);

    $records = [];                // JSON’a yazacağımız tüm satırlar

    foreach ($groupids as $gid) {
        /* ---------- Host Group bilgisi --------- */
        $groups = $zbx->call('hostgroup.get', [
            "output"   => ["groupid", "name"],
            "groupids" => $gid
        ]);

        foreach ($groups as $grp) {
            $groupname = $grp['name'];

            /* ---------- Host listesi --------- */
            $hosts = $zbx->call('host.get', [
                "output"   => ["hostid", "host", "name", "status"],
                "groupids" => $gid
            ]);

            foreach ($hosts as $h) {
                $hostStatus = $h['status'];
                if ($hostStatus != 0) continue;          // yalnızca aktif hostlar

                /* ---------- Item listesi --------- */
                $items = $zbx->call('item.get', [
                    "output"   => [
                        "itemid","type","name","hostid",
                        "units","lastclock","lastvalue",
                        "status","state"
                    ],
                    "hostids"  => $h['hostid'],
                    "groupids" => $gid
                ]);

                foreach ($items as $it) {
                    if ($it['status'] != 0 || $it['state'] != 0) continue; // etkin item

                    /* --------- vendorname'i 'dl-' ön ekinden türet -------- */
                    $vendorname = null;
                    if (preg_match('/^dl-(.+)$/', $groupname, $m)) {
                        $vendorname = $m[1];
                    }

                    /* --------- Kaydı diziye ekle -------- */
                    $records[] = [
                        "vendorname"          => $vendorname,
                        "groupname"           => $groupname,
                        "groupid"             => $gid,
                        "hostname"            => $h['name'],
                        "hostid"              => $it['hostid'],
                        "itemid"              => $it['itemid'],
                        "name"                => $it['name'],
                        "type"                => $it['type'],
                        "units"               => $it['units'],
                        "lastvalue"           => $it['lastvalue'],
                        "timestamp_unix_utc"  => (int) $it['lastclock']
                    ];
                }
            }
        }
    }

    /* ----------------------------------------------------------------------
       3) Dosyaya yaz
       ---------------------------------------------------------------------- */
    $jsonFlags = JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT;
    if (file_put_contents($outputFile, json_encode($records, $jsonFlags)) === false) {
        throw new RuntimeException("output.json yazılamadı ($outputFile).");
    }

    echo "Toplam " . count($records) . " kayıt output.json dosyasına yazıldı.\n";

} catch (ZabbixApiException $e) {
    echo "==== Zabbix API Hatası ===\n";
    echo "Kod: {$e->getCode()}\nMesaj: {$e->getMessage()}\n";
    exit(1);
} catch (Exception $e) {
    echo "==== Genel Hata ===\n";
    echo "Kod: {$e->getCode()}\nMesaj: {$e->getMessage()}\n";
    exit(1);
}
?>
