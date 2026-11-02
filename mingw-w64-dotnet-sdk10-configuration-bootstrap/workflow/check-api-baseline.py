"""Check the known original-source discrepancy without declaring strict nullable parity."""
from pathlib import Path
import json,sys
out=Path(sys.argv[1]);here=Path(__file__).resolve().parent;report=json.loads((out/'results.json').read_text());expected=json.loads((here/'original-primitives-nullable-discrepancy.json').read_text())
primitive=report['projects']['Microsoft.Extensions.Primitives']
assert primitive['exit_code']==1 and primitive['comparison']==expected
assert expected['expected_entries']==142 and expected['total_differences']==0 and len(expected['nullable_annotation_differences'])==1
for name,p in report['projects'].items():
 assert p['comparison']['total_differences']==0
 if name!='Microsoft.Extensions.Primitives':assert p['exit_code']==0 and not p['comparison']['nullable_annotation_differences']
assert sum(p['comparison']['expected_entries'] for p in report['projects'].values())==299
(out/'baseline-results.json').write_text(json.dumps(dict(CLR_contract_entries=299,CLR_missing_extra_changed=0,strict_Primitives_nullable_contract_gate_exit_code=1,strict_Primitives_nullable_contract_gate_passed=False,original_Primitives_nullable_discrepancies=1,exact_known_discrepancy_report_matched=True,other_three_configuration_nullable_gates_passed=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS299 original CLR entries and exact original StringValues discrepancy; strict Primitives nullable gate remains FAILED (1 difference)')
