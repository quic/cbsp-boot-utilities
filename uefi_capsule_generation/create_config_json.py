# --------------------------------------------------------------------
# Copyright (c) 2024 Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause-Clear
# --------------------------------------------------------------------

import traceback
import json
import os
from collections import OrderedDict

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

    config_json_data['Payloads'] = [Payloads_entry_dict]

    with open('config.json', 'w') as json_file:
        json.dump(config_json_data, json_file, indent=4)
