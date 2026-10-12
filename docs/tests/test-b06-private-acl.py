"""Real Windows ACL regression without depending on PowerShell Security module loading."""
from pathlib import Path
import importlib.util,os,subprocess,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];s=importlib.util.spec_from_file_location('secrets',ROOT/'scripts/prepare-b06-secrets.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
@unittest.skipUnless(os.name=='nt','Windows-specific ACL implementation')
class PrivateAcl(unittest.TestCase):
 def test_protection_and_three_expected_principals_even_with_broken_module_search(self):
  with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'PSModulePath':str(Path(folder)/'missing-modules')}):
   m.protect_windows(Path(folder));script=Path(folder)/'verify.ps1';script.write_text("param([string]$target); $ErrorActionPreference='Stop'; $acl=[System.IO.Directory]::GetAccessControl($target,[System.Security.AccessControl.AccessControlSections]::Access); if(-not $acl.AreAccessRulesProtected){throw 'UNPROTECTED'}; $allowed=@([System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value,'S-1-5-18','S-1-5-32-544'); $rules=@($acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier])); if($rules.Count -ne 3){throw 'WRONG_RULE_COUNT'}; foreach($r in $rules){if($r.IsInherited -or $r.IdentityReference.Value -notin $allowed -or $r.AccessControlType -ne 'Allow' -or $r.FileSystemRights -ne 'FullControl'){throw 'WRONG_PRIVATE_GRANT'}}; [Console]::WriteLine('ACL_REGRESSION_PASS')",encoding='utf-8');r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),folder],capture_output=True,text=True);self.assertEqual(0,r.returncode,r.stderr);self.assertIn('ACL_REGRESSION_PASS',r.stdout)
if __name__=='__main__':unittest.main()
