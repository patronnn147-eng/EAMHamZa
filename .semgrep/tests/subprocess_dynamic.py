import os
import subprocess


def run_backup_bad(filename):
    # ruleid: subprocess-dynamic-input
    subprocess.run(f"tar -czf backup.tar.gz {filename}", shell=True)


def run_backup_good(filename):
    # ok: subprocess-dynamic-input
    subprocess.run(["tar", "-czf", "backup.tar.gz", filename])


def call_bad(cmd_var):
    # ruleid: subprocess-dynamic-input
    subprocess.call("cmd " + cmd_var, shell=True)


def system_bad(filename):
    # ruleid: subprocess-dynamic-input
    os.system("rm -f " + filename)


def system_good():
    # ok: subprocess-dynamic-input
    os.system("echo hello")
