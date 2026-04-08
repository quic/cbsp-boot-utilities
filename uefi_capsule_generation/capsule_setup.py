# --------------------------------------------------------------------
# Copyright (c) 2025 Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause-Clear
# --------------------------------------------------------------------


__prog__        = "Sync and build edk2"
__version__     = "1.0"
__description__ = "Downloads the required files from github and builds" \
                    "required executables for linux/windows.\n"


import requests
import subprocess
import os
import shutil
import platform
import stat
import argparse
import validators
import traceback


edk2_branch="edk2-stable202008"
edk2_git_repo_sync_url = "https://github.com/tianocore/edk2.git"
edk2_windows_base_tools_url = "https://github.com/tianocore/edk2-BaseTools-win32.git"
generate_capsule_py_sync_url = "https://raw.githubusercontent.com/tianocore" \
    "/edk2/ef91b07388e1c0a50c604e5350eeda98428ccea6/BaseTools/Source/Python" \
    "/Capsule/GenerateCapsule.py"
basetools_common_sync_url = "https://github.com/tianocore/edk2/tree/" \
    "edk2-stable202008/BaseTools/Source/Python/Common"


###
# Linux functions #
###


def run_make_command_linux(edk2_dir_path):

    if not os.path.exists(edk2_dir_path) or not os.path.isdir(edk2_dir_path):
        print(f"\n\nDirectory '{edk2_dir_path}' does not exist.\n\n")
        return f"Directory '{edk2_dir_path}' does not exist."

    base_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        os.chdir(edk2_dir_path)
        subprocess.run(['make'], check=True)
    except:
        print("\n", traceback.format_exc())
        print("\nFailed to build edk2\n\n")
        return "Failed to build edk2"

    print(f"'make' command executed successfully in {edk2_dir_path}")
    os.chdir(base_dir)
    return True


def update_edk2_submodules_linux(edk2_dir_path):

    if not os.path.exists(edk2_dir_path):
        print(f"\n\nDirectory '{edk2_dir_path}' does not exist\n\n")
        return f"Directory '{edk2_dir_path}' does not exist"

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(edk2_dir_path)

    try:
        subprocess.run( \
            ['git', 'submodule', 'update', '--init', '--recursive'], \
            check=True)
    except:
        print(f"\n\nFailed executing: subprocess.run(" \
              "['git', 'submodule', 'update', '--init', '--recursive']," \
            " check=True)\n\n")
        print(traceback.format_exc())

        return "Failed executing: subprocess.run(" \
            "['git', 'submodule', 'update', '--init', '--recursive']," \
            "check=True)"

    os.chdir(base_dir)
    print("initialization done")
    return True


def print_header_sync_edk2_linux(clone_dir):
    print("\n\n\n")
    print("Copying edk2")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print(f"Github URL: {edk2_git_repo_sync_url}")
    print(f"Clone local path: {clone_dir}")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print("\n\n")


def sync_edk2_linux(edk2_git_repo_sync_url, edk2_dir_path):

    if os.path.exists(edk2_dir_path) and os.path.isdir(edk2_dir_path):
        print(f"Directory '{edk2_dir_path}' already esists")
        return f"Directory '{edk2_dir_path}' already esists"

    print_header_sync_edk2_linux(edk2_dir_path)

    try:
        subprocess.run(
            ['git', 'clone', edk2_git_repo_sync_url, edk2_dir_path], 
            check=True)
        print(f"Repository cloned into {edk2_dir_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository: {e}")
        return "Error cloning repository"


    if update_edk2_submodules_linux(edk2_dir_path) != True:
        print("Failed to sync submodules")
        return "Failed to sync submodules"

    return True


def sync_and_build_edk2_linux(edk2_dir_path, c_dir):

    if platform.system() == 'Linux':
        edk2_get_repo_sync_stats = sync_edk2_linux(edk2_git_repo_sync_url, 
                                                   edk2_dir_path)
        if edk2_get_repo_sync_stats != True:
            return edk2_get_repo_sync_stats

        edk2_build_stats = run_make_command_linux(c_dir)

        if edk2_build_stats != True:
            return edk2_build_stats

    return True


###
# Windows functions #
###


def print_header_sync_edk2_win(clone_dir, git_command):
    print("\n\n\n")
    print("Copying edk2")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print(f"Github URL: {edk2_windows_base_tools_url}")
    print(f"Clone local path: {clone_dir}")
    print(f"git clone command: {git_command}")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print("\n\n")


def sync_edk2_win(clone_dir):

    if os.path.exists(clone_dir):
        print("\n\nedk2  found\n\n")
        return "edk2  found"

    # git_command = "git clone %s %s" % (edk2_git_repo_sync_url, clone_dir)
    git_command = "git clone %s %s" % (edk2_windows_base_tools_url, clone_dir)
    print_header_sync_edk2_win(clone_dir, git_command)

    if not validators.url(edk2_git_repo_sync_url):
        print(f"Invalid URL: {edk2_git_repo_sync_url}")
        print(f"Terminated copying edk2")
        return f"Invalid URL: {edk2_git_repo_sync_url}"

    try:
        subprocess.run('cmd /c ' + git_command, check=True)
        print("\n\n\nEdk2 cloning complete\n\n")
    except:
        print("\n", traceback.format_exc())
        print("\nFailed to sync edk2 from github\n\n")
        return "Failed to sync edk2 from github"
    
    return True


def update_edk2_submodules_win(edk2_dir_path):
    try:
        os.chdir(edk2_dir_path)
        subprocess.run(['git', 'submodule', 'update', '--init'], check=True)
    except:
        print(f"Failed executing: subprocess.run(" \
              "['git', 'submodule', 'update', '--init'], check=True)")
        print(traceback.format_exc())
        return False
    return True


def build_edk2(edk2_dir_path):

    try:
        os.chdir(edk2_dir_path)
        subprocess.run(['edksetup.bat', 'Rebuild'], check=True)
    except:
        print(f"Failed executing: subprocess.run(" \
              "['edksetup.bat', 'Rebuild'], check=True)")
        print(traceback.format_exc())
        return "Failed to build edk2"
    return True


def build_edk2_win(edk2_dir_path, full_build):

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(edk2_dir_path)

    if full_build:
        if not update_edk2_submodules_win(edk2_dir_path):
            os.chdir(base_dir)
            return "Failed to sync submodules"
    else:
        print("\n\nFull build not enabled, skipping submodules sync\n\n")

    if not build_edk2(edk2_dir_path):
        os.chdir(base_dir)
        return "Failed to build Edk2"

    os.chdir(base_dir)
    print("\n\nEdk2 build complete\n\n\n")
    return True


def sync_and_build_edk2_win(clone_dir, full_build):

    if platform.system() == 'Windows':
        edk2_get_repo_sync_stats = sync_edk2_win(clone_dir)
        if edk2_get_repo_sync_stats != True:
            return edk2_get_repo_sync_stats


###
# Common functions #
###


def force_delete_folder(folder_path):

    if platform.system() == 'Windows':
        try:
            subprocess.run(
                ['rmdir', '/S', '/Q', folder_path],
                check=True, shell=True)
            print(f"Folder deleted successfully: {folder_path}")

        except Exception as e:
            print(f"Failed to delete Dir {folder_path}")
            print(e)

    if platform.system() == 'Linux':
        try:
            shutil.rmtree(folder_path)
            print(f"Dir deleted successfully: {folder_path}")

        except Exception as e:
            print(f"Failed to delete Dir {folder_path}")
            print(e)


def del_file(file_path):
    try:
        os.remove(file_path)
        print(f"File deleted successfully: {file_path}")

    except:
        print(f"Failed to delete file: {file_path}")
        print(traceback.format_exc())


def print_header_sync_generate_capsule_py(generate_capsule_py_file_path_abs):
    print("\n\n\n")
    print("Copying GenerateCapsule.py")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print(f"Github URL: {generate_capsule_py_sync_url}")
    print(f"Clone local path: {generate_capsule_py_file_path_abs}")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print("\n\n")


def sync_generate_capsule_py(generate_capsule_py_sync_url, 
                             generate_capsule_py_file_path_abs):

    if os.path.exists(generate_capsule_py_file_path_abs):
        print("\n\nGenerateCapsule.py  found\n\n")
        return "GenerateCapsule.py  found"

    print_header_sync_generate_capsule_py(generate_capsule_py_file_path_abs)

    if not validators.url(generate_capsule_py_sync_url):
        print(f"Invalid URL: {generate_capsule_py_sync_url}")
        print(f"Terminated copying GenerateCapsule.py")
        return f"Invalid URL: {generate_capsule_py_sync_url}"

    try:
        response = requests.get(generate_capsule_py_sync_url)
        if response.status_code == 200:
            with open(generate_capsule_py_file_path_abs, 'wb') as file:
                file.write(response.content)
            print('GenerateCapsule.py File downloaded successfully\n\n')
    except:
        print(traceback.format_exc())
        print('\nFailed to download file\n\n')
        return "Failed to download file"
    return True


def copy_GenFv(base_dir_abs, genfv_path_win, genfv_local_path_abs):

    if os.path.exists(genfv_local_path_abs):
        print("\n\nGenFv.exe  found\n\n")
        return "GenFv.exe  found"

    try:
        shutil.copy(genfv_path_win, base_dir_abs)
        print(f"Copied {genfv_path_win} to {base_dir_abs}")
    except:
        print(f"\n\nFailed to copy GenFv.exe from {genfv_path_win} to " \
              f"{base_dir_abs}\n\n")
        print(traceback.format_exc())
        return f"Failed to copy GenFv.exe from {genfv_path_win} to " \
            f"{base_dir_abs}"

    return True


def copy_GenFfs(base_dir_abs, genffs_path_win, genffs_local_path_abs):

    if os.path.exists(genffs_local_path_abs):
        print("\n\nGenFfs.exe  found\n\n")
        return "GenFfs.exe  found"

    try:
        shutil.copy(genffs_path_win, base_dir_abs)
        print(f"Copied {genffs_path_win} to {base_dir_abs}")
    except:
        print(f"\n\nFailed to copy GenFv.exe from {genffs_path_win} to " \
              f"{base_dir_abs}\n\n")
        print(traceback.format_exc())
        return f"Failed to copy GenFv.exe from {genffs_path_win} to " \
                f"{base_dir_abs}"

    return True


def print_header_sync_common_dir(branch,
                                 common_dir,
                                 local_path,
                                 Common_dir_path):
    print("\n\n\n")
    print("Copying common dir")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print(f"Github URL: {edk2_git_repo_sync_url}")
    print(f"Branch: {branch}")
    print(f"Clone local path: {Common_dir_path}")
    print(f"Local temp working path: {local_path}")
    print(f"Final copy path: {common_dir}")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print("\n\n")


def sync_single_dir(edk2_git_repo_sync_url, branch, target_dir, local_path):

    if not os.path.exists(local_path):
        os.makedirs(local_path)

    try:
        subprocess.run(['git', 'init'], cwd=local_path)
        subprocess.run(
            ['git', 'remote', 'add', 'origin', edk2_git_repo_sync_url],
            cwd=local_path)
        subprocess.run(
            ['git', 'config','core.sparseCheckout', 'true'],
            cwd=local_path)

        sparse_checkout_file = os.path.join(local_path,
                                            '.git',
                                            'info',
                                            'sparse-checkout')
        print(f"\n\nsparse_checkout_file: {sparse_checkout_file}\n\n")
        if not os.path.exists(os.path.join(local_path, '.git', 'info')):
            os.mkdir(os.path.join(local_path, '.git', 'info'))
        with open(sparse_checkout_file, 'w') as f:
            f.write("%s/\n" % (target_dir))

        subprocess.run(['git', 'pull', 'origin', branch], cwd=local_path)
    except:
        print(f"Failed to sync common dir")
        print(traceback.format_exc())
        return "Failed to sync common dir"

    return True


def sync_common_dir(base_dir_abs, common_dir_local_sync_path_abs):

    temp_local_working_dir_path = os.path.join(base_dir_abs,
                                               "Common_sync")
    Common_dir_path = os.path.join(temp_local_working_dir_path,
                                   "BaseTools",
                                   "Source",
                                   "Python",
                                   "Common")

    if os.path.exists(common_dir_local_sync_path_abs):
        print("\n\nCommon dir found\n\n")
        return "Common dir found"

    print_header_sync_common_dir(edk2_branch,
                                 common_dir_local_sync_path_abs,
                                 temp_local_working_dir_path,
                                 Common_dir_path)

    try:
        sync_single_dir(edk2_git_repo_sync_url,
                        edk2_branch,
                        target_dir='BaseTools/Source/Python/Common',
                        local_path=temp_local_working_dir_path)
        print("\n\nCompleted common folder sync\n\n")
    except:
        print("\n", traceback.format_exc())
        print("\nFailed to sync common dir from github\n\n")
        return "Failed to sync common dir from github"

    shutil.copytree(Common_dir_path, 
                    common_dir_local_sync_path_abs)

    if os.path.exists(temp_local_working_dir_path):
        force_delete_folder(temp_local_working_dir_path)

    return True


def clean_build(clean_build, 
                generate_capsule_py_file_path_abs, 
                edk2_sync_local_path_abs, 
                genffs_path_abs, 
                genfv_path_abs, 
                common_dir_local_sync_path_abs):

    if not clean_build:
        return True
    print("Clean build enabled")

    if os.path.exists(generate_capsule_py_file_path_abs):
        del_file(generate_capsule_py_file_path_abs)
    else:
        print(f"File not found: {generate_capsule_py_file_path_abs}, skipping delete")

    if os.path.exists(edk2_sync_local_path_abs):
        force_delete_folder(edk2_sync_local_path_abs)
    else:
        print(f"Dir not found: {edk2_sync_local_path_abs}, skipping delete")

    if os.path.exists(genffs_path_abs):
        del_file(genffs_path_abs)
    else:
        print(f"File not found: {genffs_path_abs}, skipping delete")

    if os.path.exists(genfv_path_abs):
        del_file(genfv_path_abs)
    else:
        print(f"File not found: {genfv_path_abs}, skipping delete")

    if os.path.exists(common_dir_local_sync_path_abs):
        force_delete_folder(common_dir_local_sync_path_abs)
    else:
        print(f"Dir not found: {common_dir_local_sync_path_abs}, skipping delete")

    return True


def print_stats(sync_generate_capsule_py_stats,
                sync_and_build_edk2_win_stats,
                copy_GenFfs_win_stats,
                copy_GenFv_win_stats,
                sync_common_dir_stats):

    print("\n\n\n")
    print("Capsule setup status:")
    print("--------------------------------------------------------------" \
          "------------------------------------")

    if sync_generate_capsule_py_stats == True:
        print("Downloaded GenerateCapsule.py successfully")
    else:
        print(f"Downloading GenerateCapsule.py failed: " \
              f"{sync_generate_capsule_py_stats}")

    if sync_and_build_edk2_win_stats == True:
        print("Downloaded and Built EDK2 successfully")
    else:
        print(f"Downloading and Building EDK2 failed: " \
              f"{sync_and_build_edk2_win_stats}")

    if copy_GenFfs_win_stats == True:
        print("Copied GenFfs successfully")
    else:
        print(f"Copying GenFfs failed: {copy_GenFfs_win_stats}")

    if copy_GenFv_win_stats == True:
        print("Copied GenFv successfully")
    else:
        print(f"Copying GenFv failed: {copy_GenFv_win_stats}")

    if sync_common_dir_stats == True:
        print("Downloaded Common directory successfully")
    else:
        print(f"Downloading Common directory failed: {sync_common_dir_stats}")
    print("--------------------------------------------------------------" \
          "------------------------------------")
    print("\n\n")


def Main(args):

    if platform.system() == "Linux":

        base_dir_abs = os.path.dirname(os.path.abspath(__file__))
        generate_capsule_py_file_path_abs = os.path.join(base_dir_abs,
                                                         'GenerateCapsule.py')
        edk2_sync_local_path_abs = os.path.join(base_dir_abs, 'edk2')
        c_dir = os.path.join(edk2_sync_local_path_abs,
                             'BaseTools',
                             'Source',
                             'C')
        genffs_sync_path_linux_abs = os.path.join(c_dir, 'bin', 'GenFfs')
        genfv_sync_path_linux_abs = os.path.join(c_dir, 'bin', 'GenFv')
        genffs_local_path_abs = os.path.join(base_dir_abs, 'GenFfs')
        genfv_local_path_abs = os.path.join(base_dir_abs, 'GenFv')
        common_dir_local_sync_path_abs = os.path.join(base_dir_abs, 'Common')

        clean_build(args.clean_build,
                    generate_capsule_py_file_path_abs,
                    edk2_sync_local_path_abs,
                    genffs_local_path_abs,
                    genfv_local_path_abs,
                    common_dir_local_sync_path_abs)

        sync_generate_capsule_py_stats = sync_generate_capsule_py(
                                            generate_capsule_py_sync_url, 
                                            generate_capsule_py_file_path_abs)
        sync_and_build_edk2_win_stats = sync_and_build_edk2_linux(
                                            edk2_sync_local_path_abs, 
                                            c_dir)
        copy_GenFfs_win_stats = copy_GenFfs(base_dir_abs, 
                                            genffs_sync_path_linux_abs, 
                                            genffs_local_path_abs)
        copy_GenFv_win_stats = copy_GenFv(base_dir_abs, 
                                          genfv_sync_path_linux_abs, 
                                          genfv_local_path_abs)
        sync_common_dir_stats = sync_common_dir(
                                            base_dir_abs, 
                                            common_dir_local_sync_path_abs)

        print_stats(sync_generate_capsule_py_stats,
                    sync_and_build_edk2_win_stats,
                    copy_GenFfs_win_stats,
                    copy_GenFv_win_stats,
                    sync_common_dir_stats)
            
    if platform.system() == "Windows":

        base_dir_abs = os.path.dirname(os.path.abspath(__file__))
        generate_capsule_py_file_path_abs = os.path.join(base_dir_abs,
                                                         'GenerateCapsule.py')
        edk2_sync_local_path_abs = os.path.join(base_dir_abs, 'edk2')
        genffs_sync_path_win_abs = os.path.join(edk2_sync_local_path_abs,
                                                'GenFfs.exe')
        genfv_sync_path_win_abs = os.path.join(edk2_sync_local_path_abs,
                                               'GenFv.exe')
        genffs_local_path_abs = os.path.join(base_dir_abs, 'GenFfs.exe')
        genfv_local_path_abs = os.path.join(base_dir_abs, 'GenFv.exe')
        common_dir_local_sync_path_abs = os.path.join(base_dir_abs, 'Common')

        clean_build(args.clean_build,
                    generate_capsule_py_file_path_abs,
                    edk2_sync_local_path_abs,
                    genffs_local_path_abs,
                    genfv_local_path_abs,
                    common_dir_local_sync_path_abs)

        sync_generate_capsule_py_stats = sync_generate_capsule_py(
                                            generate_capsule_py_sync_url,
                                            generate_capsule_py_file_path_abs)
        
        sync_and_build_edk2_win_stats = sync_and_build_edk2_win(
                                            edk2_sync_local_path_abs,
                                            args.full_build)
        
        copy_GenFfs_win_stats = copy_GenFfs(
                                    base_dir_abs,
                                    genffs_sync_path_win_abs,
                                    genffs_local_path_abs)
        
        copy_GenFv_win_stats = copy_GenFv(
                                    base_dir_abs,
                                    genfv_sync_path_win_abs,
                                    genfv_local_path_abs)
        
        sync_common_dir_stats = sync_common_dir(
                                    base_dir_abs,
                                    common_dir_local_sync_path_abs)

        print_stats(sync_generate_capsule_py_stats,
                    sync_and_build_edk2_win_stats,
                    copy_GenFfs_win_stats,
                    copy_GenFv_win_stats,
                    sync_common_dir_stats)


def main():
    parser = argparse.ArgumentParser(
        prog=__prog__,
        description="VERSION: " + __version__ + ", " + __description__,
        conflict_handler='resolve',
    )
    parser.add_argument("-c", "--clean_build",
                        dest='clean_build', default=False,
                        help="If set to 'True', deletes any existing "
                             "folders/files and download again. "
                             "Default - 'False'")
    parser.add_argument("-f", "--full_build",
                        dest='full_build', default=False,
                        help="If set to 'True', downloads additional "
                             "submodules for a full edk2 build. "
                             "These submodules and full build are not "
                             "required for capsule update. "
                             "Default - 'False'")
    args = parser.parse_args()
    Main(args)


if __name__ == "__main__":
    main()
 