# Capsule Generation Tools

## 1. Introduction to the Capsule Generation Tools

Capsule Generation Tools are specialized utilities designed to create capsule
files, which are essential for performing firmware updates on various devices.
These tools streamline the process of packaging firmware updates into a format
that can be easily deployed and applied to the target hardware.

## 2. Overview of the Capsule Generation Tools

The tools can be run on both Windows and Linux environments, providing
flexibility for different development setups. By using OpenSSL for certificate
generation and signing, the tools ensure that the firmware updates are secure
and authenticated.

## 3. Working of the Host Signing Tool

### 3.1 Pre-requisites to Run the Tool

**For Linux:**

1. **OpenSSL**: A toolkit for the Transport Layer Security (TLS) and Secure
   Sockets Layer (SSL) protocols.
1. **Python3**: A programming language widely used for scripting and
   automation.
1. **GIT**: version control system.

**For Windows:**

1. **OpenSSL**: Same as above.
1. **Python3**: Same as above.
1. **GIT**: version control system.
1. **Visual Studio with C++ Development Tools**: An integrated development
   environment (IDE) from Microsoft, including tools for C++ development.

Before starting the capsule generation process, you need to generate OpenSSL
certificates as mentioned in
[Capsule-Based System Firmware Update - Generate Keys][capsule-keys].
These certificates should be placed in a separate folder named 'Certificates'.

[capsule-keys]: https://github.com/tianocore/tianocore.github.io/wiki/Capsule-Based-System-Firmware-Update-Generate-Keys

Sample Certificates folder:

```
QcFMPCert.pem
QcFMPRoot.pub.pem
QcFMPSub.pub.pem
```

The `QcFMPRoot.cer` (or `NewRoot.cer`) should be converted to a hex value.

Use `BinToHex.py` to convert `NewRoot.cer` to a Hex value:

```
python3 BinToHex.py  NewRoot.cer  NewRoot.inc

Usage:
BintoHex.py  <InputFile> <OutputFile>
```

This `NewRoot.inc` contains the cert value, which needs to be provided in the BOOT DT [will be part of `xbl_config.elf`] for QCS6490,QCS9100,QCS8300,QCS615 or in UEFI DT [will be part of `uefi_dtbs.elf`] for IQ-X7181,IQ-X5121,Kaanapali,SM8750,QRB2210-RB1,CQ2390M targets at node
`/sw/uefi/uefiplat/QcCapsuleRootCert` using QDTE tool.

For more information on the QDTE Tool, refer to the
[QDTE Tool documentation][qdte-tool].

[qdte-tool]: https://docs.qualcomm.com/bundle/publicresource/topics/80-70017-4/tools.html?vproduct=1601111740013072&version=1.3&facet=Boot#qdte


*Please Note - for QLI Hamoa/Purwa uefi_dtbs.elf needs to compressed using xz tool and then flashed.
```
xz -k uefi_dtbs.elf

Usage:
xz -k  <InputFile>
-k : to keep the original uncompressed file
```


### 3.2 Setting QcCapsuleRootCert Without QDTE (for targets - QCS6490, QCS9100, QCS8300, QCS615)

As an alternative to QDTE, you can patch the certificate directly into
`xbl_config.elf` using `xblconfig_parser.py` and `set_dtb_property.py`.

1. Extract all DTB payloads from `xbl_config.elf`:

   ```sh
   python3 xblconfig_parser.py xbl_config.elf dump --out-dir ./out
   ```

1. Patch the `QcCapsuleRootCert` property into the appropriate DTB.
   The target is the DTB containing the `/sw/uefi/uefiplat` node
   (typically a `post-ddr` DTB):

   ```sh
   python3 set_dtb_property.py \
     out/<post-ddr-dtb>.dtb \
     /sw/uefi/uefiplat \
     QcCapsuleRootCert \
     @list:QcFMPRoot.inc \
     out/<post-ddr-dtb>_patched.dtb
   ```

   The `@list:QcFMPRoot.inc` argument reads the integer list produced by
   `BinToHex.py` and encodes it as 32-bit big-endian words into the DTB
   property.

1. Replace the patched DTB back into `xbl_config.elf`. Use the program
   header index (`<ph_num>`) shown by the `dump` step above:

   ```sh
   python3 xblconfig_parser.py xbl_config.elf replace \
     <ph_num> out/<post-ddr-dtb>_patched.dtb xbl_config_patched.elf
   ```

## 4. Steps to Generate Capsule Files

Clone the repository and enter the
`cbsp-boot-utilities/uefi_capsule_generation/` directory:

```sh
git clone https://github.com/quic/cbsp-boot-utilities.git
```

1. **Setup the Environment:**

   ```sh
   python3 capsule_setup.py
   ```

   This clones edk2, builds `GenFfs`/`GenFv`, and downloads
   `GenerateCapsule.py` alongside the scripts.

   If you already have a local edk2 build, you can skip this step and
   pass `--edk2-path <dir>` to `FVCreation.py` / `capsule_creator.py`
   instead (see steps 4 and 5).

1. **Generate Firmware Version bin File:**

   ```sh
   python3 SYSFW_VERSION_program.py \
     -Gen -FwVer 0.0.A.B -LFwVer 0.0.0.0 -O SYSFW_VERSION.bin
   ```

   Where A and B are the version numbers:

   - `-Gen`: Generate a new firmware version file.
   - `-FwVer`: Specifies the firmware version.
   - `-LFwVer`: Specifies the lowest firmware version.
   - `-O`: Output file name.

   To print the Firmware Versions in the `.bin` file:

   ```sh
   python3 SYSFW_VERSION_program.py --PrintAll SYSFW_VERSION.bin
   ```

1. **Generate/Update FvUpdate.xml with Firmware entries:**

  * For targets IQ-X7181-EVK, IQ-X5121, Kaanapali-MTP, SM8750-MTP - Manually update FvUpdate.xml (UpdateFvXml.py not supported yet)

   This script generates the `FvUpdate.xml` file with firmware entries:

   ```sh
   python3 UpdateFvXml.py -S <StorageType> -T <Target>
   ```

   or using a local partition configuration file:

   ```sh
   python3 UpdateFvXml.py -F <partition.conf>
   ```

   - `-S <StorageType>`: Storage type, `EMMC` or `UFS`.
   - `-T <Target>`: Target platform, `QCS6490`, `QCS9100`, `QCS8300`,
     or `QCS615`.
   - `-F <partition.conf>`: Path to a local `partition.conf` file.
   - `--ptool-path <dir>`: Path to an existing `qcom-ptool` checkout.
     When provided, the repository is not cloned from GitHub.

   Once `FvUpdate.xml` is generated, update the `Operation` field for
   each firmware entry as needed. By default the operation is set to
   `IGNORE`.

1. **Create Firmware Volume (FV):**

   - Ensure the `/Images` folder contains all the required firmware images
     for Capsule generation.
   - Update `FvUpdate.xml` with `FwEntry` for each firmware image,
     referencing the corresponding image in the `/Images` folder.
   - Refer to `FirmwarePartitions.md` for Partitions related information.

   ```sh
   python3 FVCreation.py firmware.fv "-FvType" "SYS_FW" \
     "FvUpdate.xml" SYSFW_VERSION.bin Images/
   ```

   - `firmware.fv`: The firmware volume file.
   - `-FvType`: Type of firmware volume.
   - `FvUpdate.xml`: XML file for firmware update.
   - `SYSFW_VERSION.bin`: The firmware version file generated in the
     previous step.
   - `Images/`: Directory containing the images.
   - `--edk2-path <dir>`: Path to an existing edk2 directory with built
     `GenFfs`/`GenFv` tools. When provided, `capsule_setup.py` does not
     need to be run. On Linux the binaries are resolved from
     `<dir>/BaseTools/Source/C/bin/`.

1. **Update JSON Parameters:**

   ```sh
   python3 UpdateJsonParameters.py \
     -j config.json \
     -f SYS_FW \
     -b SYSFW_VERSION.bin \
     -pf firmware.fv \
     -p Certificates/QcFMPCert.pem \
     -x Certificates/QcFMPRoot.pub.pem \
     -oc Certificates/QcFMPSub.pub.pem \
     -g <ESRT GUID>
   ```

   - `-j config.json`: JSON configuration file.
   - `-f SYS_FW`: Firmware type.
   - `-b SYSFW_VERSION.bin`: Firmware version file.
   - `-pf firmware.fv`: Firmware volume file.
   - `-p Certificates/QcFMPCert.pem`: Certificate file.
   - `-x Certificates/QcFMPRoot.pub.pem`: Root public certificate.
   - `-oc Certificates/QcFMPSub.pub.pem`: Subordinate public certificate.
   - `-g <ESRT GUID>`: ESRT GUID.

   ESRT GUIDs:

   - QCS6490 ESRT GUID: `6F25BFD2-A165-468B-980F-AC51A0A45C52`
   - QCS9100 ESRT GUID: `78462415-6133-431C-9FAE-48F2BAFD5C71`
   - QCS8300 ESRT GUID: `8BF4424F-E842-409C-80BE-1418E91EF343`
   - QCS615 ESRT GUID: `9FD379D2-670E-4BB3-86A1-40497E6E17B0`
   - QRB2210-RB1 ESRT GUID: `A2C156D8-ABBF-49B4-9F3D-8C13-4DDE-977B`
   - CQ2390M ESRT GUID: `BD3276F4-219C-452F-9E59-B15D8F242B75`
   - IQ-X7181 ESRT GUID: `0F6D58FC-2258-4D27-9E23-D77219B0897C`
   - IQ-X5121 ESRT GUID: `185A798B-13B2-4595-BD08-E2770A4BB190`
   - Kaanapali ESRT GUID: `2153308F-BE7C-404A-8605-1FF25E8703B9`
   - SM8750 ESRT GUID: `3409BE01-F1F6-40C2-9336-192FD96606F4`
   


2. **Generate the Capsule File:**

   ```sh
   python3 GenerateCapsule.py \
     -e -j config.json \
     -o <capsule_name>.cap \
     --capflag PersistAcrossReset \
     -v
   ```

   - `-e`: Enable capsule generation.
   - `-j config.json`: JSON configuration file.
   - `-o <capsule_name>.cap`: Output capsule file.
   - `--capflag PersistAcrossReset`: Flag to persist across reset.
   - `-v`: Verbose mode.

   To dump info from the Capsule headers:

   ```sh
   python3 GenerateCapsule.py --dump-info capsule.cap
   ```

## 5. Alternative: Master Script

Instead of the above 5 steps, use the following master script to run all
steps at once:

```sh
python3 capsule_creator.py \
  -fwver 0.0.A.B \
  -lfwver 0.0.0.0 \
  -config config.json \
  -p Certificates/QcFMPCert.pem \
  -x Certificates/QcFMPRoot.pub.pem \
  -oc Certificates/QcFMPSub.pub.pem \
  -guid <ESRT GUID> \
  -capsule <capsule_name>.cap \
  -images /Images \
  -setup \
  -S <StorageType> \
  -T <Target>
```

 - `-S <StorageType>`: Storage type, `EMMC` or `UFS`.
 - `-T <Target>`: Target platform, `QCS6490`, `QCS9100`, `QCS8300`,
   or `QCS615`.

The **-setup** parameter is optional and can be used for the initial setup.
You can omit it in subsequent runs.

If you have a local edk2 build and/or a local `qcom-ptool` checkout,
you can skip the setup step entirely by providing their paths directly:

```sh
python3 capsule_creator.py \
  -fwver 0.0.A.B \
  -lfwver 0.0.0.0 \
  -config config.json \
  -p Certificates/QcFMPCert.pem \
  -x Certificates/QcFMPRoot.pub.pem \
  -oc Certificates/QcFMPSub.pub.pem \
  -guid <ESRT GUID> \
  -capsule <capsule_name>.cap \
  -images /Images \
  -S <StorageType> \
  -T <Target> \
  --edk2-path /path/to/edk2 \
  --ptool-path /path/to/qcom-ptool
```

 - `--edk2-path <dir>`: Path to an existing edk2 directory with built
   `GenFfs`/`GenFv` tools. `GenerateCapsule.py` and its `Common/`
   dependency are also resolved from this tree.
 - `--ptool-path <dir>`: Path to an existing `qcom-ptool` checkout.
   When provided, the repository is not cloned from GitHub.
