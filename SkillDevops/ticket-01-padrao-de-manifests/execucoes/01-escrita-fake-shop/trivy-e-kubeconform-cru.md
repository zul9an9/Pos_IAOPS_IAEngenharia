$ trivy config manifests/orion-prod   # catálogo cru, sem trivyignore
20-postgres.yaml (kubernetes)
Tests: 100 (SUCCESSES: 99, FAILURES: 1)
Failures: 1 (UNKNOWN: 0, LOW: 0, MEDIUM: 1, HIGH: 0, CRITICAL: 0)
KSV-0125 (MEDIUM): Container postgres in statefulset orion-postgres (namespace: orion-prod) uses an image from an untrusted registry.
30-web.yaml (kubernetes)
Tests: 101 (SUCCESSES: 99, FAILURES: 2)
Failures: 2 (UNKNOWN: 0, LOW: 0, MEDIUM: 2, HIGH: 0, CRITICAL: 0)
KSV-0125 (MEDIUM): Container migrate in deployment orion-web (namespace: orion-prod) uses an image from an untrusted registry.
KSV-0125 (MEDIUM): Container web in deployment orion-web (namespace: orion-prod) uses an image from an untrusted registry.

$ kubeconform -summary -strict manifests/orion-prod
Summary: 7 resources found in 3 files - Valid: 7, Invalid: 0, Errors: 0, Skipped: 0
