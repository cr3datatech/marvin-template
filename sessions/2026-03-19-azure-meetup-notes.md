# Azure Meetup Notes — 19 March 2026

## Speakers
- **Sakari** — Opening / Azure Landscape
- **Vesa** — Data track
- **Jouni** — App track

---

## Learning Gaps Identified
- **Need to learn: Azure AI Foundry** — critical for RAG chatbot & data-to-LLM workflows (flagged pre-meetup)

---

## Tools & Resources Noted
- **pencil.dev** — mentioned during meetup (context TBC)
- **Playwright** — mentioned during meetup (context TBC)

---

## Power Lab Ideas Discussed (Pre-Meetup)

### From Sakari's track
- **"My First Azure Landing Zone"** — deploy a basic landing zone using CAF templates (hub-spoke network, one workload subscription, basic policies)

### From Vesa's track
- **"AI-Ready Data Pipeline on Azure"** — Ingest → Azure Data Factory → Azure Storage → Fabric/Databricks → expose to LLM
- **"Chat with Your Data using Azure AI Foundry + Fabric"** — Azure AI Search + Fabric lakehouse → RAG chatbot via AI Foundry

### From Jouni's track
- **"Deploy a Containerised App on Azure with AI Copilot Assistance"** — Use Claude/GitHub Copilot to write Bicep IaC, deploy to Azure Container Apps
- **"GitHub Actions CI/CD Pipeline for an Azure App"** — Full deploy pipeline: PR → build → test → deploy to Azure Container Apps

### Top pick (pre-meetup)
**"AI-Ready Data Pipeline → RAG Chatbot"** (Vesa track) — natural extension of AI Foundry blueprint, core Azure data services, high LinkedIn/internal visibility

---

## Key Takeaways

### Who Gets Hired
- **Employers will hire AI-knowledgeable people**
- Learn AI in the context of *your* current role:
  - **Dev** → AI-assisted coding (Claude Opus or OpenAI Codex 5.3)
  - **DevOps / Platform Engineer** → AI-assisted IaC (Bicep/Terraform), CI/CD (GitHub/AzDO), KQL for monitoring, developer platform thinking
  - **Security Specialist** → Entra ID + (Jussi's session TBC)
  - **Cloud Architect (foundational)** → WAF + CAF, landing zones, hub-spoke networking, policies
  - **Cloud Architect (data/AI)** → AI-assisted, code-based Fabric/Databricks + Azure Data Factory + Azure Storage, then streaming/real-time

---

### Conclusion: Embracing the Future of Data in the AI Era
- **Focus on Business Needs** — Shift from specific tools to understanding business requirements and effective data integration for impactful solutions
- **Adaptability and Learning** — Continuous learning and adaptability are critical to staying relevant in the rapidly evolving AI and data landscape
- **Microsoft Fabric and Skills** — Leveraging Microsoft Fabric alongside strong foundational skills future-proofs careers and unlocks AI's full potential

---

### 🔥 Is Waterfall Making a Comeback? (Spec-Driven AI Dev)

| Classic Waterfall | Spec-Driven AI Dev |
|---|---|
| Big upfront design documents | Detailed specs before AI generates code |
| Sequential handoffs between phases | Human architects, AI executes |
| Change is expensive and late | Change is cheap — AI rebuilds fast |
| Died because humans couldn't predict requirements upfront | Works because **the spec IS the product** |

> **The spec-writing muscle is suddenly important again.**

**Why this matters for Craig:**
- As a cloud architect, you're not the one writing the code — you're the one writing the spec the AI executes
- Deep business understanding + precise spec-writing = the architect's new superpower
- This validates the WAF/CAF/architecture-first thinking — the *design* is more valuable than ever

---

## Power Lab Ideas (Post-Meetup)
*(To be filled in after the meetup)*

---

## Follow-ups & Contacts
*(To be filled in after the meetup)*
