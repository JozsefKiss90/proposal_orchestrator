# Collector fixtures (R12a)

Synthetic stack outputs, parameter files and collector inputs for
`tests/tools/test_collect_evidence_v2.py`. Every id has the real shape and none is real: account
`111122223333`, Regions `eu-west-9`, `eu-south-9` and `ap-east-9`, ids `0f…`/`0e…`, names `fx-orch-…`.
A test checks that no value here equals a value of the real outputs or parameter files.
The outputs files start with a UTF-8 BOM, as Windows PowerShell's `Out-File -Encoding utf8` writes them.
