# Integration Checklist - Quick Reference

**Copy this checklist for any VibeMind cross-submodule integration task**

---

## Integration: [SOURCE] → [TARGET]

**Date Started**: ___________
**Complexity**: ○ Simple  ○ Medium  ○ Complex
**Pattern**: ○ Sequential  ○ Parallel  ○ Test-Driven  ○ Spike
**Estimated Time**: ___________

---

## Phase 1: Research & Planning

### Research (Instance 1)
- [ ] Read `[source]/README.md` or `[source]/CLAUDE.md`
- [ ] Read `[target]/README.md` or `[target]/CLAUDE.md`
- [ ] Check `VibeMind/docs/` for existing integration docs
- [ ] Identify all files that need changes

### Data Flow Analysis
- [ ] Understand who initiates (source → target or bidirectional?)
- [ ] Define what data moves between components
- [ ] Identify technology barriers (language, process, network)

### Interface Design
- [ ] Document input format/signature
- [ ] Document output format/signature
- [ ] Define error handling strategy
- [ ] Plan fallback behavior (if integration fails)

### Integration Plan
- [ ] Create `VibeMind/docs/INTEGRATION_PLAN_[X]_TO_[Y].md`
- [ ] Document data flow diagram
- [ ] List all file changes needed
- [ ] Define testing strategy
- [ ] Get review/approval (if working with team)

---

## Phase 2: Pattern Selection

### Decision Questions
- [ ] Same language? (YES = easier / NO = need bridge)
- [ ] Same process? (YES = function calls / NO = IPC)
- [ ] Time critical? (YES = parallel / NO = sequential OK)
- [ ] High risk? (YES = test-driven / NO = sequential OK)
- [ ] Unclear feasibility? (YES = spike first / NO = proceed)

### Pattern Selected: ___________

**Rationale**:
_____________________________________________
_____________________________________________

### Instance Assignments
- [ ] **Instance 1 (Root)**: ________________________
- [ ] **Instance 2 (Sakana)**: ______________________
- [ ] **Instance 3 (The Brain)**: ___________________
- [ ] **Instance 4 (Moire)**: _______________________
- [ ] **Instance 5 (Electron)**: ____________________

---

## Phase 3: Implementation

### If Sequential Pattern:
- [ ] Step 1: Provider component implemented (Instance ___)
- [ ] Step 2: Consumer component implemented (Instance ___)
- [ ] Step 3: Integration tested (Instance 1)

### If Parallel Pattern:
- [ ] Both components started simultaneously
- [ ] Coordination file created: `VibeMind/docs/COORDINATION_[DATE].md`
- [ ] Mock interface used initially (if needed)
- [ ] Integration point reached
- [ ] Mocks replaced with real implementation

### If Test-Driven Pattern:
- [ ] Integration tests written FIRST (Instance 1)
- [ ] Tests confirmed to fail (expected!)
- [ ] Provider implemented to pass tests
- [ ] Consumer implemented to pass tests
- [ ] All tests passing

### If Spike & Stabilize Pattern:
- [ ] Quick spike completed (proof-of-concept)
- [ ] Spike reviewed and learnings documented
- [ ] Spike code deleted/archived
- [ ] Proper implementation started with chosen pattern

---

## Phase 4: Code Changes

### Source Submodule: [NAME]
- [ ] File 1: `______________________________` (created/modified)
- [ ] File 2: `______________________________` (created/modified)
- [ ] File 3: `______________________________` (created/modified)
- [ ] Tests: `______________________________` (created/modified)
- [ ] Committed: `git commit -m "_____________________"`
- [ ] Pushed: `git push origin [branch]`

### Target Submodule: [NAME]
- [ ] File 1: `______________________________` (created/modified)
- [ ] File 2: `______________________________` (created/modified)
- [ ] File 3: `______________________________` (created/modified)
- [ ] Tests: `______________________________` (created/modified)
- [ ] Committed: `git commit -m "_____________________"`
- [ ] Pushed: `git push origin [branch]`

### VibeMind Root
- [ ] Submodule ref updated: `git add [source-submodule]`
- [ ] Submodule ref updated: `git add [target-submodule]`
- [ ] Integration tests added: `tests/integration/test_[x]_[y].py`
- [ ] Committed: `git commit -m "integrate: [summary]"`

---

## Phase 5: Testing

### Unit Tests (Per Submodule)
- [ ] Source submodule tests pass: `pytest [source]/tests/`
- [ ] Target submodule tests pass: `pytest [target]/tests/`
- [ ] Test coverage acceptable (>80% for integration code)

### Integration Tests (VibeMind Root)
- [ ] Happy path test passes
- [ ] Error handling test passes (source unavailable)
- [ ] Error handling test passes (target unavailable)
- [ ] Error handling test passes (invalid data)
- [ ] Error handling test passes (timeout)
- [ ] Performance test passes (latency < ___ ms)
- [ ] Memory test passes (no leaks over 5 min run)

### End-to-End Tests (If Applicable)
- [ ] Full pipeline tested: User input → Result
- [ ] Manual testing completed
- [ ] Edge cases tested: ________________________

---

## Phase 6: Performance & Quality

### Performance Checks
- [ ] Latency measured: ________ ms (target: < ___ ms)
- [ ] Memory usage measured: ________ MB (acceptable?)
- [ ] CPU usage measured: ________ % (acceptable?)
- [ ] Throughput measured (if relevant): ________ ops/sec

### Code Quality
- [ ] Code reviewed (Instance 1 or peer)
- [ ] No hardcoded paths or secrets
- [ ] Error messages are clear and actionable
- [ ] Logging added for debugging
- [ ] Comments added for complex logic

### Failure Modes Handled
- [ ] Source component unavailable → Graceful fallback
- [ ] Target component unavailable → Graceful fallback
- [ ] Network timeout (if applicable) → Retry logic
- [ ] Invalid response → Clear error message
- [ ] Version mismatch → Version check on startup

---

## Phase 7: Documentation

### Code Documentation
- [ ] Docstrings added to all new functions
- [ ] Type hints added (Python) / JSDoc (TypeScript)
- [ ] Inline comments for complex logic
- [ ] API reference updated (if applicable)

### Integration Documentation
- [ ] `VibeMind/docs/INTEGRATION_PLAN_[X]_TO_[Y].md` updated with results
- [ ] `VibeMind/README.md` updated (Integration Points section)
- [ ] Submodule CLAUDE.md updated (if relevant)
  - [ ] `[source]/CLAUDE.md` mentions integration
  - [ ] `[target]/CLAUDE.md` mentions integration

### User-Facing Documentation (If Applicable)
- [ ] Feature announcement written
- [ ] Usage examples added
- [ ] Troubleshooting guide updated

### Technical Documentation
- [ ] Architecture diagram updated (if needed)
- [ ] Version compatibility documented
- [ ] Breaking changes logged (if any)
- [ ] Migration guide written (if needed)

---

## Phase 8: Deployment & Monitoring

### Pre-Deployment
- [ ] All tests passing on main branch
- [ ] Code reviewed and approved
- [ ] Documentation complete
- [ ] Rollback plan defined

### Deployment
- [ ] Merged to main branch (source submodule)
- [ ] Merged to main branch (target submodule)
- [ ] VibeMind root updated with new submodule refs
- [ ] Tagged release (if appropriate): `git tag v[version]`

### Post-Deployment Monitoring
- [ ] Integration logs checked (first 24 hours)
- [ ] Performance metrics monitored
- [ ] Error rate tracked
- [ ] User feedback collected

### Maintenance Plan
- [ ] Monitoring dashboard created (if needed)
- [ ] Alert thresholds defined (error rate, latency)
- [ ] Ownership assigned (who maintains this integration?)
- [ ] Deprecation timeline defined (if temporary integration)

---

## Phase 9: Retrospective

### What Went Well ✅
_____________________________________________
_____________________________________________
_____________________________________________

### What Could Be Improved 🔧
_____________________________________________
_____________________________________________
_____________________________________________

### Lessons Learned 📝
_____________________________________________
_____________________________________________
_____________________________________________

### Future Enhancements 🚀
- [ ] Enhancement 1: _____________________________
- [ ] Enhancement 2: _____________________________
- [ ] Enhancement 3: _____________________________

---

## Sign-Off

**Integration Completed By**: ___________
**Date Completed**: ___________
**Total Time Spent**: ___________
**Status**: ○ Success  ○ Partial Success  ○ Deferred

**Notes**:
_____________________________________________
_____________________________________________
_____________________________________________

---

## Quick Reference: Common Patterns

### Python → Python (Same Repo)
```python
from [module] import [function]
result = function(input)
```

### Python → Python (Different Submodule)
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "[submodule]"))
from [module] import [function]
```

### TypeScript → Python (Via IPC)
```typescript
// Electron main process
ipcMain.handle('call-python', async (event, data) => {
  const result = await pythonBridge.call(data);
  return result;
});
```

### C++ → Python (Via pybind11)
```cpp
// C++ side
PYBIND11_MODULE(module_name, m) {
    m.def("function_name", &cpp_function);
}

// Python side
import module_name
result = module_name.function_name(input)
```

### REST API Integration
```python
import requests
response = requests.post('http://localhost:8765/api/endpoint', json=data)
result = response.json()
```

### WebSocket Integration
```typescript
const ws = new WebSocket('ws://localhost:8765/stream');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleData(data);
};
```

---

**Related Documentation:**
- [INTEGRATION_WORKFLOW_GUIDE.md](INTEGRATION_WORKFLOW_GUIDE.md) - Complete methodology
- [VIBECODING_WORKFLOW.md](VIBECODING_WORKFLOW.md) - 5-instance daily workflow
- [PARALLEL_VIBECODING.md](PARALLEL_VIBECODING.md) - Orchestration patterns
