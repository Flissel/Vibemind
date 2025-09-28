MCPTools Scaffold: kubernetes.ops

Purpose: Placeholder for Kubernetes operational MCP server/tool (kubectl apply/get/describe, kustomize/helm hooks).
Status: scaffold only (no transport/runtime implementation yet)

Notes:
- Intended to expose K8s operations via MCP.
- Configure via kubeconfig/env/config.yaml. Never commit secrets.
- Add an inactive servers.json entry when implementing.