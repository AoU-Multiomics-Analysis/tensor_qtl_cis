"""Validate runtime and execute the rendered command with localized file paths."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import WDL

ROOT = Path(__file__).resolve().parents[1]

class WorkflowTests(unittest.TestCase):
    def test_runtime(self):
        text = (ROOT / 'tensorqtl_cis_nominal.wdl').read_text()
        self.assertTrue(text.startswith('version 1.0'))
        self.assertIn('predefinedMachineType: "g2-standard-16"', text)
        self.assertIn('gpuType: "nvidia-l4"', text)
        self.assertNotIn('nvidia-tesla-p100', text)

    def run_task(self, optional=False, cloud=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = dict(prefix='test', memory=64, disk_space=100,
                          num_threads=16, num_gpus=1, num_preempt=0)
            keys = ['plink_pgen', 'plink_pvar', 'plink_psam', 'phenotype_bed', 'covariates']
            if optional:
                keys += ['interaction', 'phenotype_groups']
            for key in keys:
                folder = root / (key + " space '$literal")
                folder.mkdir()
                path = folder / key
                path.write_text(key)
                inputs[key] = str(path)
            if cloud:
                inputs[cloud] = 'gs://bucket/input.tsv'
            task = WDL.load(str(ROOT / 'tensorqtl_cis_nominal.wdl')).tasks[0]
            env = WDL.values_from_json(inputs, task.available_inputs)
            stdlib = WDL.StdLib.Base(task.effective_wdl_version)
            for decl in task.inputs:
                if decl.name not in [b.name for b in env]:
                    env = env.bind(decl.name, decl.expr.eval(env, stdlib) if decl.expr else WDL.Value.Null())
            command = task.command.eval(env, stdlib).value
            package = root / 'tensorqtl'
            package.mkdir()
            (package / '__init__.py').write_text('')
            (package / '__main__.py').write_text(
                'import sys,json,pathlib\n'
                'for ext in ["pgen","pvar","psam"]:\n'
                ' assert pathlib.Path(sys.argv[1]+"."+ext).read_text()=="plink_"+ext\n'
                'pathlib.Path("argv.json").write_text(json.dumps(sys.argv[1:]))\n')
            result = subprocess.run(['bash', '-c', command], cwd=root, text=True,
                capture_output=True, env={**os.environ, 'PYTHONPATH':str(root)})
            args = json.loads((root/'argv.json').read_text()) if (root/'argv.json').exists() else None
            return result, args, inputs

    def test_localized_files_and_absent_options(self):
        result, args, inputs = self.run_task()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(args[1], inputs['phenotype_bed'])
        self.assertIn('cis_nominal', args)
        self.assertNotIn('--interaction', args)
        self.assertNotIn('--phenotype_groups', args)

    def test_optional_localized_files(self):
        result, args, inputs = self.run_task(optional=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for key in ['interaction', 'phenotype_groups']:
            self.assertEqual(args[args.index('--'+key)+1], inputs[key])

    def test_reject_unlocalized_uri(self):
        for key in ['plink_pgen', 'plink_pvar', 'plink_psam', 'phenotype_bed',
                    'covariates', 'interaction', 'phenotype_groups']:
            with self.subTest(key=key):
                result, args, _ = self.run_task(optional=True, cloud=key)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('localization', result.stderr.lower())
                self.assertIsNone(args)

    def test_no_workflow_scope_file_writes(self):
        doc = WDL.load(str(ROOT / 'tensorqtl_cis_nominal.wdl'))
        def visit(node):
            if isinstance(node, WDL.Expr.Apply):
                self.assertNotIn(node.function_name, {'write_lines','write_tsv','write_map','write_json'})
            for child in node.children:
                visit(child)
        visit(doc.workflow)

if __name__ == '__main__':
    unittest.main()
