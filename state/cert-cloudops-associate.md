# AWS CloudOps Engineer - Associate

**Status:** Active
**Target date:** TBD
**Exam code:** CO-C02

---

## Resources

- [AWS Partner Certification Readiness: CloudOps Engineer – Associate](https://skillbuilder.aws/learning-plan/7ENQJKBYDU/aws-partner-certification-readiness--cloudops-engineer--associate/4RX4VXZ8F9) — Official AWS Skill Builder learning plan. Covers all exam domains in a structured path. Recommended starting point.
- [Udemy: AWS Certified CloudOps Associate](https://www.udemy.com/course/aws-certified-cloudops-associate/) — Stephane Maarek (25 hours listed, ~55–60h conservative). Practical scenarios and exam-focused.

---

## Exam Domains

| Domain | Weight |
|--------|--------|
| 1. Monitoring, Logging & Remediation | 20% |
| 2. Reliability & Business Continuity | 16% |
| 3. Deployment, Provisioning & Automation | 18% |
| 4. Security & Compliance | 16% |
| 5. Networking & Content Delivery | 18% |
| 6. Cost & Performance Optimization | 12% |

---

## Key Services

- CloudWatch, CloudTrail, Config, Systems Manager
- Auto Scaling, ELB, RDS Multi-AZ, Route 53
- CloudFormation, OpsWorks, CodeDeploy
- IAM, KMS, Security Hub, GuardDuty
- VPC, CloudFront, Direct Connect
- Cost Explorer, Trusted Advisor, Compute Optimizer

---

## Study Plan

> **Conservative rule:** 2× video time + notes + hands-on. Heavier sections (lots of lessons, hands-on services) padded further.
> All Udemy times are from the course content screenshots — treat them as a floor, not a target.

### Week 1 — EC2 Core + SSM
**Sections:** S3 (remaining), S4, S5

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S3 | EC2 for CloudOps | 18 (2 done) | 1h 12m | ~2h remaining |
| S4 | AMI - Amazon Machine Image | 9 | 32m | ~1h |
| S5 | Managing EC2 at Scale (SSM) | 20 | 1h 19m | ~3h |

**Weekly total: ~6h** | Focus: EC2 deep dive, AMIs, SSM Run Command, Patch Manager, Parameter Store

---

### Week 2 — High Availability & Scalability
**Sections:** S6

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S6 | EC2 High Availability and Scalability | 30 | 2h 9m | ~4.5h |

**Weekly total: ~4.5h** | Focus: ALB, ASG, target groups, scaling policies — S6 is 30 lessons, don't rush it

---

### Week 3 — CloudFormation
**Sections:** S7

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S7 | CloudFormation for CloudOps | 37 | 2h 22m | ~5.5h |

**Weekly total: ~5.5h** | Focus: Stacks, change sets, drift detection, StackSets, cfn-init — biggest lesson count, do hands-on labs

---

### Week 4 — Serverless + Storage Core
**Sections:** S8, S9, S10, S11, S12

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S8 | Lambda for CloudOps | 7 | 25m | ~1h |
| S9 | EC2 Storage and Data Management - EBS and EFS | 10 | 50m | ~1.5h |
| S10 | Amazon S3 Introduction | 14 | 43m | ~1.5h |
| S11 | Advanced Amazon S3 & Athena | 13 | 56m | ~2h |
| S12 | Amazon S3 Security | 8 | 20m | ~45m |

**Weekly total: ~6.75h** | Focus: Lambda triggers, EBS snapshots & types, S3 lifecycle, replication, bucket policies, encryption

---

### Week 5 — Advanced Storage, CDN & Databases
**Sections:** S13, S14, S15

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S13 | Advanced Storage Section | 7 | 26m | ~1h |
| S14 | CloudFront | 13 | 55m | ~2h |
| S15 | Databases for CloudOps | 19 | 1h 21m | ~3h |

**Weekly total: ~6h** | Focus: Storage Gateway, CloudFront behaviours & caching, RDS Multi-AZ, Aurora, ElastiCache

---

### Week 6 — Monitoring, Account Management & DR
**Sections:** S16, S17, S18

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S16 | Monitoring, Auditing and Performance | 35 | 1h 55m | ~4h |
| S17 | AWS Account Management | 20 | 1h 8m | ~2.5h |
| S18 | Disaster Recovery | 4 | 12m | ~30m |

**Weekly total: ~7h** | Focus: CloudWatch Logs/Alarms/Insights, Config rules, CloudTrail, Organisations, Control Tower, DR strategies — Domain 1 & 2 core

---

### Week 7 — Security, Identity & Route 53
**Sections:** S19, S20, S21

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S19 | Security and Compliance for CloudOps | 24 | 1h 24m | ~3h |
| S20 | Identity | 8 | 25m | ~1h |
| S21 | Networking - Route 53 | 29 | 1h 49m | ~3.5h |

**Weekly total: ~7.5h** | Focus: GuardDuty, Security Hub, Macie, KMS, IAM policies, Route 53 routing policies & health checks

---

### Week 8 — VPC Deep Dive
**Sections:** S22

| Section | Topic | Lessons | Udemy | Conservative |
|---------|-------|---------|-------|-------------|
| S22 | Networking - VPC | 50 | 2h 52m | ~6.5h |

**Weekly total: ~6.5h** | Focus: Subnets, NACLs, SGs, VPN, Direct Connect, Transit Gateway, VPC Peering — 50 lessons, biggest in the course, take your time

---

### Week 9 — Other Services + Exam Prep
**Sections:** S23, S24, S25 + revision

| Activity | Lessons | Udemy | Conservative |
|----------|---------|-------|-------------|
| S23: Other Services | 23 | 1h 28m | ~3h |
| S24: Preparing for the Exam + Practice Exam | 7 | 12m | ~1.5h |
| S25: Congratulations | 3 | 9m | ~15m |
| Review weak domains (check notes) | — | — | ~2h |
| Full practice exam — Tutorials Dojo | — | — | ~1.5h |
| Review wrong answers in depth | — | — | ~1.5h |

**Weekly total: ~9.75h** | Goal: Score 80%+ on practice exam before booking the real one. Split this across 2 weeks if needed.

---

## Progress

| Section | Topic | Lessons | Status | Notes |
|---------|-------|---------|--------|-------|
| S1 | Introduction & Requirements | 5/5 | ✅ Done | |
| S2 | Slides and Code Download | 1/1 | ✅ Done | |
| S3 | EC2 for CloudOps | 2/18 | 🔄 In Progress | |
| S4 | AMI - Amazon Machine Image | 0/9 | ⬜ Not started | |
| S5 | Managing EC2 at Scale - SSM | 0/20 | ⬜ Not started | |
| S6 | EC2 High Availability and Scalability | 0/30 | ⬜ Not started | |
| S7 | CloudFormation for CloudOps | 0/37 | ⬜ Not started | |
| S8 | Lambda for CloudOps | 0/7 | ⬜ Not started | |
| S9 | EC2 Storage and Data Management - EBS and EFS | 0/10 | ⬜ Not started | |
| S10 | Amazon S3 Introduction | 0/14 | ⬜ Not started | |
| S11 | Advanced Amazon S3 & Athena | 0/13 | ⬜ Not started | |
| S12 | Amazon S3 Security | 0/8 | ⬜ Not started | |
| S13 | Advanced Storage Section | 0/7 | ⬜ Not started | |
| S14 | CloudFront | 0/13 | ⬜ Not started | |
| S15 | Databases for CloudOps | 0/19 | ⬜ Not started | |
| S16 | Monitoring, Auditing and Performance | 0/35 | ⬜ Not started | |
| S17 | AWS Account Management | 0/20 | ⬜ Not started | |
| S18 | Disaster Recovery | 0/4 | ⬜ Not started | |
| S19 | Security and Compliance for CloudOps | 0/24 | ⬜ Not started | |
| S20 | Identity | 0/8 | ⬜ Not started | |
| S21 | Networking - Route 53 | 0/29 | ⬜ Not started | |
| S22 | Networking - VPC | 0/50 | ⬜ Not started | |
| S23 | Other Services | 0/23 | ⬜ Not started | |
| S24 | Preparing for the Exam + Practice Exam | 0/7 | ⬜ Not started | |
| S25 | Congratulations | 0/3 | ⬜ Not started | |

---

## Practice Exam Scores

| Date | Score | Platform | Notes |
|------|-------|----------|-------|
| | | | |

---

## Notes

_Add study notes, key takeaways, and observations here as you go._
