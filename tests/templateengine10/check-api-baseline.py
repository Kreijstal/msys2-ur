"""Validate the unchanged stronger API failure; never relabel it as a passing gate."""
from pathlib import Path
import json
import sys

check = Path(sys.argv[1]).resolve()
here = Path(__file__).resolve().parent
actual = json.loads((check / 'results.json').read_text())
expected = json.loads((here / 'original-API-discrepancy.json').read_text())
assert actual['strict_API_baseline_exit_code'] == expected['strict_API_baseline_exit_code'] == 1
assert actual['strict_API_baseline_passed'] is expected['strict_API_baseline_passed'] is False
reports = {n:dict(expected_entries=r['expected_entries'],missing=r['missing']) for n,r in actual['API_reports'].items()}
assert reports == expected['API_reports']
assert len(reports)==7 and sum(len(r['missing']) for r in reports.values())==2
assert sum(r['expected_entries'] for r in reports.values())==1986
assert actual['strict_CPM_restore_policy_passed']
assert actual['owned_TemplateEngine_scan_generation_dryrun_search_json_and_cancellation_passed']
assert all(c['exit_code']==(1 if i==1 else 0) for i,c in enumerate(actual['commands']))
(check / 'baseline-results.json').write_text(json.dumps(dict(upstream_API_baseline_entries=1986,unchanged_original_missing_entries=2,strict_API_baseline_exit_code=1,strict_API_baseline_passed=False,exact_original_failure_report_retained=True,strict_CPM_restore_passed=True,runtime_checks_passed=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS runtime and exact original failure report; stronger all-seven API baseline remains FAILED with two entries')
