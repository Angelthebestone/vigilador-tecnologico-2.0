"""Verify all branch overlays parse correctly from HTML format."""
import sys
sys.path.insert(0, "src")

from vigilancia_multiagente.application.governance.contract_loader import _parse_prompt_overlay
from vigilancia_multiagente.infra.prompts.loader import load_prompt
from vigilancia_multiagente.domain.models import BranchType

branches = ["avances", "comercial", "riesgo", "pi_normativa", "competitivo", "oportunidades"]
errors = 0

for name in branches:
    text = load_prompt(f"branches/{name}")
    result = _parse_prompt_overlay(text)
    
    issues = []
    if not result.get("objective"):
        issues.append("missing objective")
    if not result.get("do_rules"):
        issues.append("missing do_rules")
    if not result.get("dont_rules"):
        issues.append("missing dont_rules")
    if not result.get("uncertainty_handling"):
        issues.append("missing uncertainty_handling")
    
    if issues:
        errors += 1
        print(f"  FAIL [{name}]: {', '.join(issues)}")
        print(f"    do_rules={result.get('do_rules')!r}")
        print(f"    dont_rules={result.get('dont_rules')!r}")
    else:
        unc = result["uncertainty_handling"].encode("ascii", "replace").decode()[:50]
        print(f"  OK   [{name}]: objective={result['objective'][:50]}")
        print(f"         do={len(result['do_rules'])} dont={len(result['dont_rules'])} uncertainty={unc}...")

print(f"\n  {len(branches) - errors}/{len(branches)} branch overlays parsed correctly")
sys.exit(errors)
