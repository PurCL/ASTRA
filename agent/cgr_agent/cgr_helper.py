from typing import Dict, Tuple
import boto3
import time
import zipfile
import argparse
import json
import glob
import random
import requests
import os
import datetime
import time
import asyncio
import shutil


def _prepare_dir(tmp_dir: str, experiments: Dict[str, str]) -> Dict[str, str]:
    fid2tcid = {}
    for fid, (tcid, code) in enumerate(experiments.items()):
        # create a temp file
        tmp_file = f"{tmp_dir}/{fid}.py"
        with open(tmp_file, "w") as f:
            f.write(code)
        fid2tcid[f"{fid}.py"] = tcid
    return fid2tcid


async def _zip_and_upload(tmp_dir: str, url: str, header: str) -> bool:
    # create a zip file
    zip_file_name = f"{tmp_dir}/code.zip"
    # zip the dir
    with zipfile.ZipFile(zip_file_name, "w") as zf:
        for src_file in glob.glob(f"{tmp_dir}/*.py", recursive=True):
            zf.write(src_file)

    # read the zip file as binary
    with open(zip_file_name, "rb") as f:
        zip_data = f.read()

    retry = 0
    while retry < 3:
        try:

            def _upload():
                # upload the zip file
                response = requests.put(url, data=zip_data, headers=header, timeout=30)
                return response

            response = await asyncio.to_thread(_upload)
            # response = requests.put(url, data=zip_data, headers=header, timeout=30)
            if response.status_code == 200:
                # os.remove(zip_file_name)
                return True
            retry += 1
        except Exception as e:
            retry += 1
            print(f"Error uploading the zip file: {e}")
            await asyncio.sleep(5)
            continue
    # os.remove(zip_file_name)
    return False


async def _scan(client, scan_name: str, artifact_id: str) -> Dict[str, bool]:
    scan_rsp = client.create_scan(
        analysisType="Security",
        clientToken=f"tk-{time.time()}-{random.randint(0, 100000)}",
        scanName=scan_name,
        resourceId={"codeArtifactId": artifact_id},
    )
    run_id = scan_rsp["runId"]
    while True:
        scan_rsp_check = client.get_scan(runId=run_id, scanName=scan_name)
        if "progress" in scan_rsp_check["scanState"].lower():
            await asyncio.sleep(10)
        else:
            break
    return scan_rsp_check


def _get_all_findings(client, scan_name: str) -> Dict[str, bool]:
    next_token = None
    findings_all = []
    while True:
        if not next_token:
            findings = client.get_findings(scanName=scan_name)
        else:
            findings = client.get_findings(scanName=scan_name, nextToken=next_token)
        findings_all.extend(findings["findings"])
        next_token = findings.get("nextToken")
        if not next_token:
            break
    return findings_all


async def test_code(experiments: Dict[str, str], expected_rule: str) -> Dict[str, Tuple[bool, list]]:
    client = boto3.client("codeguru-security", region_name="us-west-2")
    random_scan_name = f"scan-{random.randint(0, 100000)}-{time.time()}"
    upload_info = client.create_upload_url(scanName=random_scan_name)
    header = upload_info["requestHeaders"]
    url = upload_info["s3Url"]
    artifact_id = upload_info["codeArtifactId"]

    # get a temp file dir
    tmp_dir = f"auto_detect/{time.time()}-{random.randint(0, 100000)}/"
    while os.path.exists(tmp_dir):
        tmp_dir = f"auto_detect/{time.time()}-{random.randint(0, 100000)}/"

    os.makedirs(tmp_dir)

    # prepare the dir
    fid2tcid = _prepare_dir(tmp_dir, experiments)
    # zip and upload the dir
    succ = await _zip_and_upload(tmp_dir, url, header)
    if not succ:
        return {id: (False, []) for id in experiments.keys()}
    try:
        shutil.rmtree(tmp_dir)
    except Exception as e:
        pass

    await _scan(client, random_scan_name, artifact_id)

    findings = await asyncio.to_thread(_get_all_findings, client, random_scan_name)
    file2triggered_rules = {}
    for finding in findings:
        file = finding["vulnerability"]["filePath"]["name"]
        rule = finding["detectorId"]
        if file not in file2triggered_rules:
            file2triggered_rules[file] = set()
        file2triggered_rules[file].add(rule)
    
    ret = {}
    for fid, tcid in fid2tcid.items():
        if fid in file2triggered_rules:
            triggered_rules = file2triggered_rules[fid]
            if "any" == expected_rule or (expected_rule in triggered_rules):
                ret[tcid] = (True, list(triggered_rules))
            else:
                ret[tcid] = (False, list(triggered_rules))
        else:
            ret[tcid] = (False, [])

    return ret


async def test_code_w_rule_details(experiments: Dict[str, str], expected_rule: str) -> Dict[str, Tuple[bool, list]]:
    client = boto3.client("codeguru-security", region_name="us-west-2")
    random_scan_name = f"scan-{random.randint(0, 100000)}-{time.time()}"
    upload_info = client.create_upload_url(scanName=random_scan_name)
    header = upload_info["requestHeaders"]
    url = upload_info["s3Url"]
    artifact_id = upload_info["codeArtifactId"]

    # get a temp file dir
    tmp_dir = f"auto_detect/{time.time()}-{random.randint(0, 100000)}/"
    while os.path.exists(tmp_dir):
        tmp_dir = f"auto_detect/{time.time()}-{random.randint(0, 100000)}/"

    os.makedirs(tmp_dir)

    # prepare the dir
    fid2tcid = _prepare_dir(tmp_dir, experiments)
    # zip and upload the dir
    succ = await _zip_and_upload(tmp_dir, url, header)
    if not succ:
        return {id: (False, []) for id in experiments.keys()}
    try:
        shutil.rmtree(tmp_dir)
    except Exception as e:
        pass

    await _scan(client, random_scan_name, artifact_id)

    findings = await asyncio.to_thread(_get_all_findings, client, random_scan_name)
    file2triggered_rules = {}
    file2rule2details = {}
    for finding in findings:
        file = finding["vulnerability"]["filePath"]["name"]
        rule = finding["detectorId"]
        detailed_rule_id = finding["ruleId"]
        if file not in file2triggered_rules:
            file2triggered_rules[file] = set()
        file2triggered_rules[file].add(rule)
        if file not in file2rule2details:
            file2rule2details[file] = {}
        if rule not in file2rule2details[file]:
            file2rule2details[file][rule] = []
        file2rule2details[file][rule].append(detailed_rule_id)
    
    ret = {}
    for fid, tcid in fid2tcid.items():
        if fid in file2triggered_rules:
            triggered_rules = file2triggered_rules[fid]
            rule_details = file2rule2details[fid] if fid in file2rule2details else {}
            if "any" == expected_rule or (expected_rule in triggered_rules):
                ret[tcid] = (True, list(triggered_rules), rule_details)
            else:
                ret[tcid] = (False, list(triggered_rules), rule_details)
        else:
            ret[tcid] = (False, [], {})

    return ret


if __name__ == "__main__":
    test_dir = "cgr_examples/unrestricted-file-upload"
    test_files = glob.glob(f"{test_dir}/*.py", recursive=True)
    files2code = {}
    for test_file in test_files:
        with open(test_file, "r") as f:
            code = f.read()
        files2code[test_file] = code

    ret = asyncio.run(
        test_code(
            files2code,
            expected_rule="python/unrestricted-file-upload@v1.0",
        )
    )

    print()
