"""Pure tests; never invoke installation or integration main locally."""
import ast
import importlib.util
from pathlib import Path
import re
import unittest
import tempfile
import subprocess
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fixture_integration',ROOT/'integration.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class StaticTests(unittest.TestCase):
    def test_public_standard_single_job(self):
        text=(ROOT/'.github/workflows/fixture.yml').read_text()
        self.assertIn('github.event.repository.private == false',text)
        self.assertIn('runs-on: macos-26',text)
        self.assertIn('timeout-minutes: 15',text)
        self.assertEqual(re.findall(r'^  (\w+):$',text.split('jobs:\n')[1],re.M),['fixture'])
        for x in ('matrix:', 'volumes:', 'services:', 'container:', 'self-hosted', 'schedule:'):
            self.assertNotIn(x,text)
    def test_checkout_and_no_secrets(self):
        text=(ROOT/'.github/workflows/fixture.yml').read_text()
        self.assertIn('contents: read',text)
        self.assertIn('persist-credentials: false',text)
        self.assertNotIn('${{ secrets.',text)
        self.assertEqual(re.findall(r'uses: (\S+)',text),['actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683'])
    def test_environment_only_fixture(self):
        env=m.environment()
        self.assertEqual(env['HOME'],'/Users/fixture-user')
        self.assertNotIn('GITHUB_TOKEN',env)
        self.assertEqual(env['NPM_CONFIG_USERCONFIG'],'/Users/fixture-user/npm-user.conf')
        self.assertNotEqual(env['NPM_CONFIG_USERCONFIG'],env['NPM_CONFIG_GLOBALCONFIG'])
        self.assertEqual(m.fixture()['gateway']['auth']['token'],m.CANARY)
    def test_integrities_and_versions(self):
        self.assertEqual(len(m.NODE_SHA),64)
        self.assertTrue(m.PACKAGE_SRI.startswith('sha512-'))
        text=(ROOT/'integration.py').read_text()
        self.assertIn('node-v26.8.1-darwin-arm64.tar.gz',text)
        self.assertIn('openclaw-2026.10.4.tgz',text)
    def test_raw_streams_not_printed(self):
        tree=ast.parse((ROOT/'integration.py').read_text())
        prints=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='print']
        self.assertEqual(len(prints),1)
        self.assertIn("'checks': RESULTS",ast.unparse(prints[0]))
    def test_no_environment_inheritance_or_mount_commands(self):
        tree=ast.parse((ROOT/'integration.py').read_text())
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in ('environ','getenv') for n in ast.walk(tree)))
        text=(ROOT/'integration.py').read_text()
        for x in ('mount_virtiofs','rsync','auth-profiles.json',"'--omit=optional'","'--ignore-scripts'"):
            self.assertNotIn(x,text)
    def test_empty_separate_npm_configs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m.create_npm_configs(root)
            paths=[root/'npm-user.conf',root/'npm-global.conf']
            self.assertNotEqual(paths[0].stat().st_ino,paths[1].stat().st_ino)
            for path in paths:
                self.assertEqual(path.read_bytes(),b'')
                self.assertEqual(path.stat().st_mode&0o777,0o600)
            with self.assertRaises(FileExistsError): m.create_npm_configs(root)
    def test_failure_projection_hides_content(self):
        marker='FICTIONAL_PRIVATE_ERROR_CONTENT'
        for error in (ValueError(marker),m.Stop(marker),OSError(marker),
                      subprocess.TimeoutExpired(marker,1,output=marker,stderr=marker)):
            result=m.failure_details(error,'npm_install')
            self.assertNotIn(marker,str(result))
            self.assertEqual(result['stage'],'npm_install')
        self.assertEqual(m.failure_details(m.Stop('NPM_CONFIG_DUPLICATE'),'npm_install')['code'],'NPM_CONFIG_DUPLICATE')

if __name__=='__main__': unittest.main()
