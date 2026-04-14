## @file
#  Description:
#  This script opens and updates JSON file with parameters required for
#  Capsule generation.
#
# --------------------------------------------------------------------
# Copyright (c) 2024 Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause-Clear
# --------------------------------------------------------------------


import argparse
import json
import os
import subprocess
import sys
from collections import OrderedDict
import platform
import traceback


def ParseArguments():
    parser = argparse.ArgumentParser(description="Process input arguments.")
    parser.add_argument(
        "-j", "--json_file", type=str, dest="JsonFile", help="Path to input JSON file"
    )
    parser.add_argument(
        "-f", "--fw_type", type=str, dest="FwType", help="Firmware Type [SYS_FW/EC_FW]"
    )
    parser.add_argument(
        "-b",
        "--bin_file",
        type=str,
        dest="BinFile",
        help="Path to System Firmware Version Binary / Embedded Controller Firmware Binary File",
    )
    parser.add_argument(
        "-t",
        "--tool_path",
        type=str,
        dest="SigningToolPath",
        help="Path to OpenSSL signing tool",
    )
    parser.add_argument(
        "-p",
        "--private_cert",
        type=str,
        dest="OpenSslSignerPrivateCertFile",
        help="OpenSSL signer private certificate filename",
    )
    parser.add_argument(
        "-x",
        "--public_cert",
        type=str,
        dest="OpenSslTrustedPublicCertFile",
        help="OpenSSL other public certificate filename.",
    )
    parser.add_argument(
        "-oc",
        "--other_cert",
        type=str,
        dest="OpenSslOtherPublicCertFile",
        help="OpenSSL trusted public certificate filename.",
    )
    parser.add_argument(
        "-pf",
        "--payload_file",
        type=str,
        dest="Payload",
        help="Path to the payload file",
    )
    parser.add_argument("-g", "--guid", type=str, dest="Guid", help="System FMP GUID")
    args = parser.parse_args()

    return args


def create_config():

    config_json_data = OrderedDict()
    Payloads_entry_dict = OrderedDict()

    Payloads_entry_dict["Guid"] = ""
    Payloads_entry_dict["FwVersion"] = ""
    Payloads_entry_dict["LowestSupportedVersion"] = ""
    Payloads_entry_dict["MonotonicCount"] = "0x2"
    Payloads_entry_dict["HardwareInstance"] = "0x0"
    Payloads_entry_dict["UpdateImageIndex"] = "0x1"
    Payloads_entry_dict["Payload"] = ""
    Payloads_entry_dict["OpenSslSignerPrivateCertFile"] = ""
    Payloads_entry_dict["OpenSslOtherPublicCertFile"] = ""
    Payloads_entry_dict["OpenSslTrustedPublicCertFile"] = ""
    Payloads_entry_dict["SigningToolPath"] = ""

    config_json_data["Payloads"] = [Payloads_entry_dict]

    with open("config.json", "w") as json_file:
        json.dump(config_json_data, json_file, indent=4)


def ExtractEcFwVersions(StringData, SubString):
    try:
        if not StringData:
            print("Empty string data!!")
            sys.exit(1)

        if not SubString:
            print("Empty sub string data!!")
            sys.exit(1)

        offset = StringData.find(SubString)
        index = offset + len(SubString)
        FwVerMain = (ord(StringData[index + 0]) - ord("0")) * 10 + (
            ord(StringData[index + 1]) - ord("0")
        )
        FwVerSub = (ord(StringData[index + 3]) - ord("0")) * 10 + (
            ord(StringData[index + 4]) - ord("0")
        )
        FwVerTest = (ord(StringData[index + 6]) - ord("0")) * 10 + (
            ord(StringData[index + 7]) - ord("0")
        )
        version = (FwVerSub << 16) | FwVerTest
        return "0x{:08x}".format(version)

    except Exception as e:
        print("Error occurred while extracting EC version: {0}.".format(e))
        sys.exit(1)


def GetEcFirmwareInfo(args):
    EcBinFilePath = args.BinFile
    try:
        # Check if EcBinFilePath path is valid
        if not os.path.exists(EcBinFilePath):
            print("Invalid EC firmware version file: {0}".format(EcBinFilePath))
            sys.exit(1)

        with open(EcBinFilePath, "rb") as file:
            BinaryData = file.read()
            StringData = BinaryData.decode("ISO-8859-1")
            args.FwVersion = ExtractEcFwVersions(
                StringData, "EC VER:"
            )  # Retrieve EC Firmware Version
            args.LowestSupportedVersion = ExtractEcFwVersions(
                StringData, "LsFv:"
            )  # Retrieve Lowest Supported EC Firmware Version
            print(
                "EC Firmware Version is {0}, lowest supported version: {1}".format(
                    args.FwVersion, args.LowestSupportedVersion
                )
            )

    except FileNotFoundError:
        print("EC Bin File does not exist: {0}.".format(e))
        sys.exit(1)

    except Exception as e:
        print("Error occurred while reading from EC bin file: {0}.".format(e))
        sys.exit(1)


def get_python_version():
    python_version = None
    try:
        output = subprocess.check_output(["python", "--version"]).decode().strip()
        python_version_l = output.split(" ")
        python_version_no = int(python_version_l[1].split(".")[0])

        if python_version_no == 3:
            python_version = "python"
    except Exception:
        print("'python --version' command failed to execute at command line")

    if python_version is None:
        try:
            output = subprocess.check_output(["python3", "--version"]).decode().strip()
            python_version_op_l = output.split(" ")
            python_version_no = int(python_version_op_l[1].split(".")[0])
            if python_version_no == 3:
                python_version = "python3"
        except Exception:
            print("'python3 --version' command failed to execute at command line")

    if python_version is None:
        print("ERROR 'python --version' and python")
        return None

    print("python_version: ", python_version)

    return python_version


def GetSysFirmwareInfo(args):
    python_version = get_python_version()
    commands = ["-GetFwVersionHex", "-GetLSFwVersionHex"]
    SysBinPath = args.BinFile
    try:
        # Check if SysBinPath and SysFwVersion.exe path is valid
        if not os.path.exists(SysBinPath):
            print("Invalid system firmware version file: {0}".format(SysBinPath))
            sys.exit(1)

        if platform.system() == "Linux":
            SysFwExePath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "SYSFW_VERSION_program.py"
            )
            if not os.path.exists(SysFwExePath):
                print("SYSFW_VERSION_program.py not found at: {0}".format(SysFwExePath))
                sys.exit(1)

            # Call SysFwVersion.exe tool to extract the firmware version and lowest
            # supported version
            results = []
            for cmd in commands:
                try:
                    output = (
                        subprocess.check_output(
                            [python_version, SysFwExePath, cmd, SysBinPath]
                        )
                        .decode()
                        .strip()
                    )
                    results.append(output)
                except Exception as e:
                    print("Failed to execute command:{0}. Error: {1}".format(cmd, (e)))
                    sys.exit(1)

            (args.FwVersion, args.LowestSupportedVersion) = (results[0], results[1])
            print(
                "Firmware Version is {0}, lowest supported version: {1}".format(
                    args.FwVersion, args.LowestSupportedVersion
                )
            )

        if platform.system() == "Windows":
            SysFwExePath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "SYSFW_VERSION_program.py"
            )
            if not os.path.exists(SysFwExePath):
                print("SYSFW_VERSION_program.py not found at: {0}".format(SysFwExePath))
                sys.exit(1)

            # Call SysFwVersion.exe tool to extract the firmware version and lowest
            # supported version
            results = []
            for cmd in commands:
                try:
                    output = (
                        subprocess.check_output(
                            [python_version, SysFwExePath, cmd, SysBinPath]
                        )
                        .decode()
                        .strip()
                    )
                    results.append(output)
                except Exception as e:
                    print("Failed to execute command:{0}. Error: {1}".format(cmd, (e)))
                    print(traceback.format_exc())

            (args.FwVersion, args.LowestSupportedVersion) = (results[0], results[1])
            print(
                "Firmware Version is {0}, lowest supported version: {1}".format(
                    args.FwVersion, args.LowestSupportedVersion
                )
            )

    except subprocess.CalledProcessError as e:
        print("Failed to extract firmware info from sys.bin: {0}".format(e))
        sys.exit(1)

    except Exception as e:
        print("Exception in GetFirmwareInfo(): {0}".format(e))
        sys.exit(1)


def UpdateJsonFile(args):
    # Get the firmware version and lowest supported version by calling the
    # ExtractEcFwVersions()/SysFwVersion.exe and add it to the args list
    FirmwareType = args.FwType
    EcFwString = "EC_FW"
    SysFwString = "SYS_FW"
    try:
        if FirmwareType == SysFwString:
            GetSysFirmwareInfo(args)
            print("GetSysFirmwareInfo(): {0}".format(SysFwString))
        elif FirmwareType == EcFwString:
            GetEcFirmwareInfo(args)
            print("GetEcFirmwareInfo(): {0}".format(EcFwString))
        else:
            print("Neither System nor EC FirmwareType: {0}".format(FirmwareType))
            sys.exit(1)

    except Exception as e:
        print("Error occurred while reading from FirmwareType string: {0}.".format(e))
        sys.exit(1)

    JsonFile = args.JsonFile
    JsonFilePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), JsonFile)
    JsonFilePathCheckCount = 0

    while not os.path.exists(JsonFilePath) and (JsonFilePathCheckCount < 5):
        create_config()
        JsonFilePathCheckCount += 1
        pass

    if not os.path.exists(JsonFilePath):
        print("%s Not found" % (JsonFile))

    try:
        with open(JsonFile, "r") as f:
            # loading the field values in json file without changing the order
            data = json.load(f, object_pairs_hook=OrderedDict)
    except Exception as e:
        print("Exception while opening JsonFile: {0}.".format(e))
        sys.exit(1)

    exception_list = ["JsonFile", "BinFile", "FwType"]

    for i, payload in enumerate(data["Payloads"]):
        for key, value in args.__dict__.items():
            try:
                if key in exception_list:
                    continue  # Skip the keys in the exception list
                elif value and key in payload:
                    data["Payloads"][i][key] = value
                elif value:
                    print("Key {0} not found in payload {1}".format(key, i))
            except Exception as e:
                print("Exception in UpdateJsonFile(): {0}".format(e))
                sys.exit(1)

    try:
        with open(JsonFile, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Error occurred while writing to the JSON file: {0}.".format(e))
        sys.exit(1)


if __name__ == "__main__":
    args = ParseArguments()
    UpdateJsonFile(args)
