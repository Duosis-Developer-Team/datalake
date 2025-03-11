<?php
require_once "ZabbixApi.php";
use IntelliTrend\Zabbix\ZabbixApi;
use IntelliTrend\Zabbix\ZabbixApiException;

$zbx = new ZabbixApi();
///////////////////////////////////////////////////////////////////////////////////////////////////////////
$jsonFilePath = "/Datalake_Project/configuration_file.json"; // Change this to your actual path

// Read the JSON file
$jsonData = file_get_contents($jsonFilePath);

// Decode the JSON data
$config = json_decode($jsonData, true); // true converts JSON to associative array

// Extract Zabbix settings
$zabbixHostName = $config["Zabbix"]["zabbixHostName"];
$zabUrl = $config["Zabbix"]["zabUrl"];
$zabUser = $config["Zabbix"]["zabUser"];
$zabPassword = $config["Zabbix"]["zabPassword"];
///////////////////////////////////////////////////////////////////////////////////////////

$groupids = array("42","45","48", "43", "44" );
//örnek group id: array("id1","id2");
header('Content-Type: text/plain; charset=utf-8');


try {
	// disable validation off certificate and host 
	$options = array('sslVerifyPeer' => false, 'sslVerifyHost' => false);
	$zbx->login($zabUrl, $zabUser, $zabPassword, $options);

	$limit = 5;
    foreach($groupids as $t)
    {


        $paramsForHG = array(
            "output" => array("groupid","name"),
            "groupids" => $t,
        );
         $resultHG = $zbx->call('hostgroup.get',$paramsForHG);
         foreach ($resultHG as $l)
         {
             $groupname = $l['name'];
             $hostParams = array(
                "output" => array("hostid", "host", "name", "status"),
                "groupids" => $t,
                
            );
            //HostAPICall
            $result = $zbx->call('host.get',$hostParams);
        
        
            //HostForeach
            foreach ($result as $v) {
                $hostid = $v['hostid'];
                $hostname = $v['host'];
                $name = $v['name'];
                $hostStatus = $v['status'];
                //itemparams
                $paramitem = array(
                    "output" => array("itemid", "type", "name", "hostid", "units", "lastclock", "lastvalue", "status", "state"),
                    "hostids" => $hostid,
                    "groupids" => $t,
                );
            
                $itemget = $zbx->call('item.get', $paramitem);
            
                //itemForeach
                foreach ($itemget as $k) {
                    $itemid = $k['itemid'];
                    $type = $k['type'];
                    $name1 = $k['name'];
                    $hostid1 = $k['hostid'];
                    $units = $k['units'];
                    $lastclock = $k['lastclock'];
                    $lastvalue = $k['lastvalue'];
                    $itemStatus = $k['status'];
                    $state = $k['state'];
                    if ($hostStatus == 0 && $itemStatus == 0 && $state == 0) {
                     $pattern = "/^dl-(.+)$/";
     
                     if (preg_match($pattern, $groupname, $matches)) {
                         $capturedValue = $matches[1]; // The value after "dl-"
                          // Output: nameofthegroup-1
                     } else {
                         echo "No match found!";
                     }
     
                     // $groupname = mb_convert_encoding($groupname, 'UTF-8', 'auto');
                     // $capturedValue = mb_convert_encoding($capturedValue, 'UTF-8', 'auto');
                     // $name = mb_convert_encoding($name, 'UTF-8', 'auto');
                     // $name1 = mb_convert_encoding($name1, 'UTF-8', 'auto');
                     // $lastvalue = mb_convert_encoding($lastvalue, 'UTF-8', 'auto');
     
                     print "vendorname: $capturedValue \ngroupname: $groupname \nhostname: $name \nname: $name1 \nlastvalue: $lastvalue \ntimestamp unix utc: $lastclock \nitemid: $itemid \ntype: $type \nhostid: $hostid1 \nunits: $units \ngroupid: $t\n\n";
                     //\nitemStatus: $itemStatus \nhostStatus: $hostStatus \nstate: $state 
                 }
                   
                }
            }
            
         }
     

    }
} catch (ZabbixApiException $e) {
	print "==== Zabbix API Exception ===\n";
	print 'Errorcode: '.$e->getCode()."\n";
	print 'ErrorMessage: '.$e->getMessage()."\n";
	exit;
} catch (Exception $e) {
	print "==== Exception ===\n";
	print 'Errorcode: '.$e->getCode()."\n";
	print 'ErrorMessage: '.$e->getMessage()."\n";
	exit;
}
?>