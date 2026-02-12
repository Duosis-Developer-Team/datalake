# -*- coding: utf-8 -*-
import requests
from datetime import datetime, timedelta
import urllib.parse
import urllib3
import json

json_file_path = "/Datalake_Project/configuration_file.json"
with open(json_file_path, "r") as file:
    config = json.load(file)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def sql_str(value):
    if value is None:
        return "NULL"
    if not isinstance(value, str):
        value = str(value)
    escaped = value.replace("'", "''")
    return f"'{escaped}'"

def sql_null_or_value(value):
    if value is None:
        return "NULL"
    return str(value)

def fetch_netbackup_jobs_with_pagination(api_url, bearer_token):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    all_data = []
    current_url = api_url

    while current_url:
        response = requests.get(current_url, headers=headers, verify=False)
        response.raise_for_status()
        data = response.json()
        all_data.extend(data.get("data", []))
        current_url = data.get("links", {}).get("next", {}).get("href")

    return all_data

def fetch_recent_netbackup_jobs(api_url, bearer_token, minutes=15):
    now = datetime.utcnow()
    time_limit = now - timedelta(minutes=minutes)
    time_limit_iso = time_limit.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    filter_param = f"filter=lastUpdateTime%20gt%20{urllib.parse.quote(time_limit_iso)}"
    api_url = f"{api_url}?{filter_param}&page%5Blimit%5D=999&sort=-lastUpdateTime"
    return fetch_netbackup_jobs_with_pagination(api_url, bearer_token)

def generate_batched_insert_queries(records, table_name="netbackup_jobs", batch_size=20):
    queries = []
    current_batch = []

    for item in records:
        # KÖK ALANLAR
        type_val = sql_str(item.get("type"))
        id_val = sql_str(item.get("id"))

        attrs = item.get("attributes", {})

        # 70 Sütun
        jobId = sql_null_or_value(attrs.get("jobId"))
        parentJobId = sql_null_or_value(attrs.get("parentJobId"))
        activeProcessId = sql_null_or_value(attrs.get("activeProcessId"))
        jobType = sql_str(attrs.get("jobType"))
        jobSubType = sql_str(attrs.get("jobSubType"))
        policyType = sql_str(attrs.get("policyType"))
        policyName = sql_str(attrs.get("policyName"))
        scheduleType = sql_str(attrs.get("scheduleType"))
        scheduleName = sql_str(attrs.get("scheduleName"))
        clientName = sql_str(attrs.get("clientName"))
        jobOwner = sql_str(attrs.get("jobOwner"))
        jobGroup = sql_str(attrs.get("jobGroup"))
        backupId = sql_str(attrs.get("backupId"))
        destinationStorageUnitName = sql_str(attrs.get("destinationStorageUnitName"))
        destinationMediaServerName = sql_str(attrs.get("destinationMediaServerName"))
        dataMovement = sql_str(attrs.get("dataMovement"))
        streamNumber = sql_null_or_value(attrs.get("streamNumber"))
        copyNumber = sql_null_or_value(attrs.get("copyNumber"))
        priority = sql_null_or_value(attrs.get("priority"))
        compression = sql_null_or_value(attrs.get("compression"))
        state = sql_str(attrs.get("state"))
        numberOfFiles = sql_null_or_value(attrs.get("numberOfFiles"))
        estimatedFiles = sql_null_or_value(attrs.get("estimatedFiles"))
        kilobytesTransferred = sql_null_or_value(attrs.get("kilobytesTransferred"))
        kilobytesToTransfer = sql_null_or_value(attrs.get("kilobytesToTransfer"))
        transferRate = sql_null_or_value(attrs.get("transferRate"))
        percentComplete = sql_null_or_value(attrs.get("percentComplete"))
        restartable = sql_null_or_value(attrs.get("restartable"))
        suspendable = sql_null_or_value(attrs.get("suspendable"))
        resumable = sql_null_or_value(attrs.get("resumable"))
        frozenImage = sql_null_or_value(attrs.get("frozenImage"))
        transportType = sql_str(attrs.get("transportType"))
        currentOperation = sql_null_or_value(attrs.get("currentOperation"))
        sessionId = sql_null_or_value(attrs.get("sessionId"))
        numberOfTapeToEject = sql_null_or_value(attrs.get("numberOfTapeToEject"))
        submissionType = sql_null_or_value(attrs.get("submissionType"))
        auditDomainType = sql_null_or_value(attrs.get("auditDomainType"))
        startTime = sql_str(attrs.get("startTime"))
        endTime = sql_str(attrs.get("endTime"))
        activeTryStartTime = sql_str(attrs.get("activeTryStartTime"))
        lastUpdateTime = sql_str(attrs.get("lastUpdateTime"))
        childCount = sql_null_or_value(attrs.get("childCount"))
        jobPath = sql_str(attrs.get("jobPath"))
        retentionLevel = sql_null_or_value(attrs.get("retentionLevel"))
        try_val = sql_null_or_value(attrs.get("try"))
        cancellable = sql_null_or_value(attrs.get("cancellable"))
        jobQueueReason = sql_null_or_value(attrs.get("jobQueueReason"))
        kilobytesDataTransferred = sql_null_or_value(attrs.get("kilobytesDataTransferred"))
        elapsedTime = sql_str(attrs.get("elapsedTime"))
        activeElapsedTime = sql_str(attrs.get("activeElapsedTime"))
        dteMode = sql_str(attrs.get("dteMode"))
        workloadDisplayName = sql_str(attrs.get("workloadDisplayName"))
        offHostType = sql_str(attrs.get("offHostType"))

        # Yeni sütunlar
        dedupRatio = sql_null_or_value(attrs.get("dedupRatio"))
        status = sql_null_or_value(attrs.get("status"))
        profileName = sql_str(attrs.get("profileName"))
        dedupSpaceRatio = sql_null_or_value(attrs.get("dedupSpaceRatio"))
        compressionSpaceRatio = sql_null_or_value(attrs.get("compressionSpaceRatio"))
        acceleratorOptimization = sql_null_or_value(attrs.get("acceleratoroptimization"))
        assetId = sql_null_or_value(attrs.get("assetid"))
        destinationMediaId = sql_null_or_value(attrs.get("destinationmediaid"))
        dumpHost = sql_null_or_value(attrs.get("dumphost"))
        instanceDatabaseName = sql_null_or_value(attrs.get("instancedatabasename"))
        qReasonCode = sql_null_or_value(attrs.get("qreasoncode"))
        qResource = sql_str(attrs.get("qresource"))
        restoreBackupIds = sql_str(attrs.get("restorebackupids"))
        robotName = sql_str(attrs.get("robotname"))
        vaultName = sql_str(attrs.get("vaultname"))

        # INSERT sorgusu
        query = (
            f"INSERT INTO {table_name} (\"type\", \"id\", jobId, parentJobId, activeProcessId, jobType, jobSubType, "
            f"policyType, policyName, scheduleType, scheduleName, clientName, jobOwner, jobGroup, backupId, "
            f"destinationStorageUnitName, destinationMediaServerName, dataMovement, streamNumber, copyNumber, "
            f"priority, compression, state, numberOfFiles, estimatedFiles, kilobytesTransferred, kilobytesToTransfer, "
            f"transferRate, percentComplete, restartable, suspendable, resumable, frozenImage, transportType, "
            f"currentOperation, sessionId, numberOfTapeToEject, submissionType, auditDomainType, startTime, endTime, "
            f"activeTryStartTime, lastUpdateTime, childCount, jobPath, retentionLevel, \"try\", cancellable, "
            f"jobQueueReason, kilobytesDataTransferred, elapsedTime, activeElapsedTime, dteMode, workloadDisplayName, "
            f"offHostType, dedupRatio, status, profileName, dedupSpaceRatio, compressionSpaceRatio, "
            f"acceleratorOptimization, assetId, destinationMediaId, dumpHost, instanceDatabaseName, qReasonCode, "
            f"qResource, restoreBackupIds, robotName, vaultName) "
            f"VALUES ({type_val}, {id_val}, {jobId}, {parentJobId}, {activeProcessId}, {jobType}, {jobSubType}, "
            f"{policyType}, {policyName}, {scheduleType}, {scheduleName}, {clientName}, {jobOwner}, {jobGroup}, {backupId}, "
            f"{destinationStorageUnitName}, {destinationMediaServerName}, {dataMovement}, {streamNumber}, {copyNumber}, "
            f"{priority}, {compression}, {state}, {numberOfFiles}, {estimatedFiles}, {kilobytesTransferred}, "
            f"{kilobytesToTransfer}, {transferRate}, {percentComplete}, {restartable}, {suspendable}, {resumable}, "
            f"{frozenImage}, {transportType}, {currentOperation}, {sessionId}, {numberOfTapeToEject}, {submissionType}, "
            f"{auditDomainType}, {startTime}, {endTime}, {activeTryStartTime}, {lastUpdateTime}, {childCount}, {jobPath}, "
            f"{retentionLevel}, {try_val}, {cancellable}, {jobQueueReason}, {kilobytesDataTransferred}, {elapsedTime}, "
            f"{activeElapsedTime}, {dteMode}, {workloadDisplayName}, {offHostType}, {dedupRatio}, {status}, {profileName}, "
            f"{dedupSpaceRatio}, {compressionSpaceRatio}, {acceleratorOptimization}, {assetId}, {destinationMediaId}, "
            f"{dumpHost}, {instanceDatabaseName}, {qReasonCode}, {qResource}, {restoreBackupIds}, {robotName}, {vaultName});"
        )
        current_batch.append(query)

        if len(current_batch) >= batch_size:
            queries.append("\n".join(current_batch))
            current_batch = []

    if current_batch:
        queries.append("\n".join(current_batch))

    return queries

if __name__ == "__main__":

    netbackup_config = config["Netbackup"]

    api_url = netbackup_config["api_url"]
    bearer_token = netbackup_config["bearer_token"]

    try:
        nb_jobs = fetch_recent_netbackup_jobs(api_url, bearer_token)
        queries = generate_batched_insert_queries(nb_jobs, table_name="netbackup_jobs", batch_size=20)
        for q in queries:
            print(q)
    except Exception as e:
        print(f"Error: {e}")
