# Capsule Generation Tools

## 1. Introduction to the Capsule Generation Tools

Capsule Generation Tools are specialized utilities designed to create capsule files, which are essential for performing firmware updates on various devices. These tools streamline the process of packaging firmware updates into a format that can be easily deployed and applied to the target hardware.

## 2. Overview of the Capsule Generation Tools

The tools can be run on both Windows and Linux environments, providing flexibility for different development setups. By using OpenSSL for certificate generation and signing, the tools ensure that the firmware updates are secure and authenticated.

## 3. Working of the Host Signing Tool

### 3.1 Pre-requisites to Run the Tool

**For Linux:**
1. **OpenSSL**: A toolkit for the Transport Layer Security (TLS) and Secure Sockets Layer (SSL) protocols.
2. **Python3**: A programming language that is widely used for scripting and automation.
3. **GIT** : version control system.

**For Windows:**
1. **OpenSSL**: Same as above.
2. **Python3**: Same as above.
3. **GIT** : version control system.
4. **Visual Studio with C++ Development Tools**: An integrated development environment (IDE) from Microsoft, which includes tools for C++ development.

Before starting the capsule generation process, you need to generate OpenSSL certificates as mentioned in this guide. These certificates should be placed in a separate folder named 'Certificates'. The `QcFMPRoot.cer` (or `NewRoot.cer`) should be provided in the BOOT DT at `/sw/uefi/uefiplat/QcRootCer`.
Sample files available in Certificates folder:
QcFMPCert.pem
QcFMPRoot.pub.pem
QcFMPSub.pub.pem

### Steps to Generate Capsule Files

1. **Setup the Environment:**
   ```sh
   python3 capsule_setup.py 
   Note: if this fails with some error, please create a folder ../uefi_capsule_generationCommon_sync/.git/**info**
2. **Generate Firmware Version File:**
   ```sh
   python3 SYSFW_VERSION_program.py -Gen -FwVer 0.0.A.B -LFwVer 0.0.0.0 -O SYSFW_VERSION.bin
    where A, B are the version numbers
   -Gen: Generate a new firmware version file.
   -FwVer: Specifies the firmware version.
   -LFwVer: Specifies the lowest firmware version.
   -O: Output file name.
3. **Create Firmware Volume (FV):**
   ```sh
   python3 FVCreation.py firmware.fv "-FvType" "SYS_FW" "FvUpdate_UFS.xml" SYSFW_VERSION.bin Images/
   Please have the /Images folder available with all required FW images, as per FvUpdate_UFS.xml
   firmware.fv: The firmware volume file.
   -FvType: Type of firmware volume.
   FvUpdate_UFS.xml: XML file for firmware update.
   SYSFW_VERSION.bin: The firmware version file generated in the previous step.
   Images/: Directory containing the images.
4. **Update JSON Parameters:**
   ```sh
   python3 UpdateJsonParameters.py -j config.json -f SYS_FW -b SYSFW_VERSION.bin -pf firmware.fv -p Certificates/QcFMPCert.pem -x Certificates/QcFMPRoot.pub.pem -oc Certificates/QcFMPSub.pub.pem -g <FMP GUID>
   

   -j config.json: JSON configuration file.
   -f SYS_FW: Firmware type.
   -b SYSFW_VERSION.bin: Firmware version file.
   -pf firmware.fv: Firmware volume file.
   -p Certificates/QcFMPCert.pem: Certificate file.
   -x Certificates/QcFMPRoot.pub.pem: Root public certificate.
   -oc Certificates/QcFMPSub.pub.pem: Subordinate public certificate.
   -g <FMP GUID>: Firmware Management Protocol (FMP) GUID.
       FMP GUIDs:
           Kodiak FMP GUID: 6F25BFD2-A165-468B-980F-AC51A0A45C52
           Lemans FMP GUID: 78462415-6133-431C-9FAE-48F2BAFD5C71
           Monaco FMP GUID: 8BF4424F-E842-409C-80BE-1418E91EF343
5. **Generate the Capsule File:**
   ```sh
   python3 GenerateCapsule.py -e -j config.json -o <capsule_name>.cap --capflag PersistAcrossReset -v
   
   -e: Enable capsule generation.
   -j config.json: JSON configuration file.
   -o kodiak_fw_zak2.cap: Output capsule file.
   --capflag PersistAcrossReset: Flag to persist across reset.
   -v: Verbose mode.