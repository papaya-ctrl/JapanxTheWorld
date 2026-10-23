"""Observe readiness for Linux staging. Never launches a VM or relaxes limits."""
import argparse
import json
import platform
import subprocess
import psutil


def inspect():
    host=psutil.virtual_memory()
    result={'hostOS':platform.system(),'hostMachine':platform.machine(),'hostRamGiB':round(host.total/1024**3,2),'availableGiB':round(host.available/1024**3,2),'swapUsedGiB':round(psutil.swap_memory().used/1024**3,2),'dockerAvailable':False,'dockerMemoryGiB':None,'linuxExecutionAllowed':False,'reasons':[]}
    try:
        response=subprocess.run(['docker','info','--format','{{json .}}'],capture_output=True,text=True,timeout=8)
        if response.returncode==0:
            info=json.loads(response.stdout)
            result['dockerAvailable']=info.get('OSType')=='linux'
            result['dockerMemoryGiB']=round(info.get('MemTotal',0)/1024**3,2)
    except (OSError,subprocess.TimeoutExpired,json.JSONDecodeError):pass
    if not result['dockerAvailable']:result['reasons'].append('linux_docker_daemon_unavailable')
    if host.available<8*1024**3:result['reasons'].append('less_than_8_gib_available_host_memory')
    if result['dockerMemoryGiB'] is not None and result['dockerMemoryGiB']<10:result['reasons'].append('docker_vm_below_10_gib_staging_budget')
    result['linuxExecutionAllowed']=not result['reasons']
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--require-linux',action='store_true');args=parser.parse_args()
    result=inspect();print(json.dumps(result,indent=2))
    raise SystemExit(3 if args.require_linux and not result['linuxExecutionAllowed'] else 0)
