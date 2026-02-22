---
name: gsd-full-feature
description: Implement a complete feature with frontend, backend, and tests using specialist subagents
allowed-tools:
  - code_execution_tool
  - call_subordinate
---

<objective>
Implement a complete full-stack feature from description to deployment-ready code. Orchestrates specialist subagents for backend, frontend, testing, and security in sequence.
</objective>

<process>

## How to Use This Skill

Invoke this skill with a feature description as the argument. The skill orchestrates a full implementation cycle:

1. **Parse feature requirements** from the user-provided description
2. **Design the API contract** using a backend-developer subagent
3. **Implement backend endpoints** using a backend-developer subagent
4. **Create frontend components** using a frontend-developer subagent
5. **Write integration tests** using a qa-tester subagent
6. **Review for security** using a security-auditor subagent

## Spawn Backend Developer Subagent (API Design)

Use `call_subordinate` to design the API contract:
- **message**: Include the full role identity (you are a backend developer specializing in API design), the feature description, the project's existing API patterns (check `src/api/` for conventions), and request a complete API contract (endpoints, request/response schemas, authentication requirements)
- **reset**: `"true"` for a fresh context

## Spawn Backend Developer Subagent (Implementation)

Use `call_subordinate` to implement the backend:
- **message**: Include the full role identity (you are a backend developer), the API contract from the previous step, the project structure, and request implementation of all backend endpoints in `src/api/`
- **reset**: `"true"` for a fresh context

## Spawn Frontend Developer Subagent

Use `call_subordinate` to build UI components:
- **message**: Include the full role identity (you are a frontend developer), the API contract, the feature requirements, the project's component conventions (check `src/components/`), and request implementation of all UI components in `src/components/`
- **reset**: `"true"` for a fresh context

## Spawn QA Tester Subagent

Use `call_subordinate` to write tests:
- **message**: Include the full role identity (you are a QA tester), the implemented backend and frontend code locations, the API contract, and request comprehensive integration tests covering happy paths and edge cases in `tests/`
- **reset**: `"true"` for a fresh context

## Spawn Security Auditor Subagent

Use `call_subordinate` to review the implementation:
- **message**: Include the full role identity (you are a security auditor), the locations of all implemented files, and request a security review covering authentication, authorization, input validation, and common vulnerabilities (OWASP Top 10)
- **reset**: `"true"` for a fresh context

## Expected Output

After all subagents complete:
- API endpoints in `src/api/`
- React components in `src/components/`
- Tests in `tests/`
- Security review summary

</process>

<success_criteria>
- [ ] Feature requirements parsed from user description
- [ ] API contract designed and agreed
- [ ] Backend endpoints implemented
- [ ] Frontend components created
- [ ] Integration tests written
- [ ] Security review completed with no critical findings
</success_criteria>
