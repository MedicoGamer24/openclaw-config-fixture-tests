"""Official-package integration with fabricated data on a disposable macOS runner.

Never run on a personal machine. Installs software and runs official lifecycle.
No claim of a network sandbox or production configuration compatibility.
"""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parent
HOME=Path('/Users/fixture-user')
STATE=HOME/'.openclaw'
CONFIG=STATE/'openclaw.json'
RUNTIME=HOME/'runtime'
NODE=RUNTIME/'bin/node'
ENTRY=RUNTIME/'lib/node_modules/openclaw/openclaw.mjs'
NODE_SHA='6e577fd0d9db776db82306629e441a9dace416702622aebdd171c9dfaa41f4d2'
PACKAGE_SRI='sha512-+FH0StZF1tlTazM7JJGY6JePeJmhFNSRByi2Q3jXPRiLO7o4dJh2xa9Vy4Dk8Cd2ic8B7Zkf5NfEaCCWUkgqnQ=='
CANARY='FABRICATED_FIXTURE_TOKEN_NOT_A_CREDENTIAL_7291'
FIELD='agents.entries.main.tools.alsoAllow'
BASE=['message']; AFTER=BASE+['gateway']
RESULTS=[]

class Stop(Exception): pass

def record(case, ok):
    RESULTS.append({'case':case,'passed':bool(ok)})
    if not ok: raise Stop(case)

def environment():
    return {'HOME':str(HOME),'OPENCLAW_HOME':str(HOME),'OPENCLAW_STATE_DIR':str(STATE),
            'OPENCLAW_CONFIG_PATH':str(CONFIG),'PATH':str(NODE.parent)+':/usr/bin:/bin:/usr/sbin:/sbin',
            'TMPDIR':'/tmp','LANG':'C','LC_ALL':'C',
            'NPM_CONFIG_USERCONFIG':'/dev/null','NPM_CONFIG_GLOBALCONFIG':'/dev/null'}

def run(args, check=True, timeout=120):
    p=subprocess.run([str(a) for a in args],env=environment(),cwd='/tmp',
                     stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     timeout=timeout,check=False)
    if check and p.returncode: raise Stop('PROCESS_FAILED')
    return p

def download(url, destination, expected, algorithm):
    with urllib.request.urlopen(url,timeout=60) as response: data=response.read()
    digest=hashlib.new(algorithm,data).digest()
    actual=digest.hex() if algorithm=='sha256' else 'sha512-'+base64.b64encode(digest).decode()
    if actual!=expected: raise Stop('DOWNLOAD_INTEGRITY')
    with destination.open('xb') as f: f.write(data)

def fixture(baseline=BASE):
    return {'agents':{'entries':{'main':{'tools':{'alsoAllow':list(baseline)}}}},
            'tools':{'profile':'coding'},
            'gateway':{'mode':'local','auth':{'mode':'token','token':CANARY}}}

def reset(baseline=BASE):
    CONFIG.write_text(json.dumps(fixture(baseline))); CONFIG.chmod(0o600)

def field(): return json.loads(CONFIG.read_text())['agents']['entries']['main']['tools']['alsoAllow']

def cli(expected, desired, preview=False):
    args=[NODE,ENTRY,'config','set',FIELD,json.dumps(desired),'--strict-json',
          '--expect-current-json',json.dumps(expected)]
    if preview: args += ['--dry-run','--json']
    p=run(args,check=False)
    record('captured_output_has_no_fixture_canary',CANARY.encode() not in p.stdout+p.stderr)
    return p.returncode

def bootstrap(tmp):
    if HOME.exists() or HOME.is_symlink(): raise Stop('FIXTURE_TARGET_EXISTS')
    archive=tmp/'node.tgz'
    download('https://nodejs.org/dist/v26.8.1/node-v26.8.1-darwin-arm64.tar.gz',archive,NODE_SHA,'sha256')
    run(['/usr/bin/sudo','-n','mkdir',HOME])
    run(['/usr/bin/sudo','-n','chown',str(os.getuid())+':'+str(os.getgid()),HOME])
    HOME.chmod(0o700); STATE.mkdir(mode=0o700); RUNTIME.mkdir()
    run(['/usr/bin/tar','-xzf',archive,'--strip-components=1','-C',RUNTIME])
    record('exact_node',run([NODE,'--version']).stdout.strip()==b'v26.8.1')
    package=tmp/'package.tgz'
    download('https://registry.npmjs.org/openclaw/-/openclaw-2026.10.4.tgz',package,PACKAGE_SRI,'sha512')
    npm=RUNTIME/'lib/node_modules/npm/bin/npm-cli.js'
    # Explicit official lifecycle is part of installation in this disposable VM.
    # No --ignore-scripts, no --omit=optional, no lifecycle-marker/guard removal.
    run([NODE,npm,'install','--global','--prefix',RUNTIME,'--no-audit','--no-fund',package],timeout=480)
    metadata=json.loads((ENTRY.parent/'package.json').read_text())
    record('exact_openclaw',metadata.get('version')=='2026.10.4')
    # Even version/help may complete pending lifecycle: no claim of zero effects.

def generic_operation(journal, expected, desired, final_stage):
    # Minimal fixture protocol. This is not an installed guardian or its API.
    with journal.locked():
        if journal.stage() is not None: raise Stop('RECEIPT_ALREADY_USED')
        if field()!=expected: return False
        acl=run(['/bin/ls','-lde',CONFIG]).stdout.splitlines()
        if len(acl)!=1 or b'+' in acl[0].split()[0]: return False
        if cli(expected,desired,True)!=0: return False
        journal.transition(None,'prepared')
        journal.transition('prepared','started')
        if cli(expected,desired)!=0: raise Stop('UNCERTAIN_WRITE_NO_RETRY')
        if field()!=desired: raise Stop('UNCERTAIN_POSTSTATE')
        journal.transition('started',final_stage)
        return True

def tests(Journal):
    receipts=HOME/'receipts'; receipts.mkdir(mode=0o700)
    reset(); before=CONFIG.read_bytes()
    record('dry_run_does_not_check_precondition',cli(['fictional-wrong'],AFTER,True)==0 and CONFIG.read_bytes()==before)
    record('write_enforces_precondition',cli(['fictional-wrong'],AFTER)!=0 and CONFIG.read_bytes()==before)
    add=Journal(receipts/'add')
    record('apply',generic_operation(add,BASE,AFTER,'applied') and field()==AFTER)
    data=json.loads(CONFIG.read_text()); data['gateway']['port']=18790
    CONFIG.write_text(json.dumps(data)); CONFIG.chmod(0o600)
    record('rollback',generic_operation(Journal(receipts/'remove'),AFTER,BASE,'removed'))
    record('unrelated_field_preserved',json.loads(CONFIG.read_text())['gateway']['port']==18790)
    record('journal_applied',add.stage()=='applied')
    record('config_modes',CONFIG.stat().st_mode&0o777==0o600 and STATE.stat().st_mode&0o777==0o700)
    backups=list(STATE.glob('openclaw.json.bak*'))
    record('backup_present',bool(backups))
    record('backup_modes',all(p.is_file() and not p.is_symlink() and p.stat().st_mode&0o777==0o600 for p in backups))
    reset(AFTER); before=CONFIG.read_bytes()
    record('preexisting_gateway_not_removed',not generic_operation(Journal(receipts/'existing'),BASE,AFTER,'applied') and CONFIG.read_bytes()==before)
    reset(); before=CONFIG.read_bytes()
    run(['/bin/chmod','+a','everyone deny write',CONFIG])
    try:
        record('acl_admission_refuses',not generic_operation(Journal(receipts/'acl'),BASE,AFTER,'applied') and CONFIG.read_bytes()==before)
    finally: run(['/bin/chmod','-a','everyone deny write',CONFIG])
    record('multiprocess_journal',run(['/usr/bin/python3','-B',ROOT/'test_journal.py'],check=False).returncode==0)

def main():
    if sys.argv[1:]!=['--disposable-runner-only'] or platform.system()!='Darwin' or platform.machine()!='arm64':
        raise Stop('RUNNER_REQUIRED')
    # This flag is not a sandbox; authorized execution is ONLY on a fresh hosted VM.
    record('macos_major',run(['/usr/bin/sw_vers','-productVersion']).stdout.startswith(b'26.'))
    spec=importlib.util.spec_from_file_location('fixture_journal',ROOT/'journal.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='public-fixture-') as tmp:
        bootstrap(Path(tmp));tests(module.Journal)

if __name__=='__main__':
    passed=False
    try: main();passed=True
    except Exception: RESULTS.append({'case':'stopped_without_retry','passed':False})
    print(json.dumps({'passed':passed,'checks':RESULTS}))
    sys.exit(0 if passed else 1)
