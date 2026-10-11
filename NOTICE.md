# Source provenance and licensing

The files vendor/mcp_scrutiny/features.py, vendor/mcp_scrutiny/model.py,
vendor/mcp_scrutiny/data/model.json and vendor/LICENSE are unmodified copies
from bryand410/mcp-scrutiny at commit 751cdd4889b0670524597ec6c4aa80c4b1d0cefd.
The upstream project uses Apache License 2.0; the complete license is in
vendor/LICENSE. No upstream NOTICE file was present in the inspected tree.
The package initializer, experiment, fixtures, tests, check runner and documentation
are independently authored for this assay. They are offered under the same
Apache License 2.0 terms. The extension is implemented in experiment.py,
not as a modification to vendored files.

artifacts/source.json records upstream Git blob IDs and SHA256 hashes.
The runner verifies those files before scoring. Upstream corpus and training
metrics are not new experimental evidence. This assay loads the shipped model
without retraining and does not claim its stored training metrics were reproduced.
