"""Check the known original-source discrepancy without declaring strict nullable parity."""
from pathlib import Path
import json,sys
out=Path(sys.argv[1]);here=Path(__file__).resolve().parent;report=json.loads((out/'results.json').read_text());expected=json.loads((here/'original-di-nullable-discrepancy.json').read_text())
di=report['projects']['Microsoft.Extensions.DependencyInjection.Abstractions'];logging=report['projects']['Microsoft.Extensions.Logging.Abstractions']
assert di['exit_code']==1 and di['comparison']==expected
assert expected['expected_entries']==244 and expected['total_differences']==0 and len(expected['nullable_annotation_differences'])==25
assert logging['exit_code']==0 and logging['comparison']['expected_entries']==160 and not logging['comparison']['nullable_annotation_differences']
(out/'baseline-results.json').write_text(json.dumps(dict(CLR_contract_entries=404,CLR_missing_extra_changed=0,strict_DI_nullable_contract_gate_exit_code=1,strict_DI_nullable_contract_gate_passed=False,original_DI_nullable_discrepancies=25,exact_known_discrepancy_report_matched=True,logging_strict_CLR_and_nullable_contract_gate_exit_code=0,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original CLR surface404 and exact known original DI discrepancy; strict DI nullable gate remains FAILED (25 differences)')
