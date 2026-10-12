"""Adversarial public-package verification independent of current repository data."""
import unittest, tempfile, json, zipfile, importlib.util, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('delivery',ROOT/'scripts/b06-delivery.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class DeliveryGuards(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.d=Path(self.temp.name)
 def seal(self,files=None,extra=None):
  files={'docs/a.md':b'content'} if files is None else files
  inner={'format':1,'files':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}
  archive=self.d/'zj-market-b06-public.zip'
  with zipfile.ZipFile(archive,'w') as z:
   for n,b in files.items():z.writestr(n,b)
   for n,b in (extra or {}).items():z.writestr(n,b)
   z.writestr('DELIVERY-MANIFEST.json',json.dumps(inner))
  manifest=dict(inner,archive=archive.name,archiveSha256=m.sha(archive),archiveBytes=archive.stat().st_size)
  (self.d/'manifest.json').write_text(json.dumps(manifest));(self.d/'COMPLETE.json').write_text(json.dumps({'manifestSha256':m.sha(self.d/'manifest.json')}))
 def test_valid_package(self):self.seal();self.assertEqual(len(m.verify(self.d)['files']),1)
 def test_truncated_archive(self):
  self.seal();(self.d/'zj-market-b06-public.zip').write_bytes(b'corrupt')
  with self.assertRaisesRegex(RuntimeError,'ARCHIVE_CHANGED'):m.verify(self.d)
 def test_resealed_extra_member(self):
  self.seal(extra={'secret.txt':b'unexpected'})
  with self.assertRaisesRegex(RuntimeError,'UNEXPECTED_ZIP_SET'):m.verify(self.d)
 def test_resealed_path_escape(self):
  self.seal({'../escape':b'x'})
  with self.assertRaisesRegex(RuntimeError,'UNSAFE_ZIP_PATH'):m.verify(self.d)
 def test_manifest_changed(self):
  self.seal();(self.d/'manifest.json').write_text('{}')
  with self.assertRaisesRegex(RuntimeError,'MANIFEST_CHANGED'):m.verify(self.d)
 def test_private_and_build_paths(self):
  for name in ['.local/secret','docs/../secret','C:/secret','frontend/node_modules/a','target/report','tls/key.pem','private.p12','docs\\secret','/absolute']:
   with self.subTest(name=name):self.assertFalse(m.safe(name))
if __name__=='__main__':unittest.main()
