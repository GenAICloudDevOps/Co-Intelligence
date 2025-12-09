# GitLab CI Deployment Guide

This project deploys to AWS via GitLab CI using `deploy.sh`. Use this doc to set up and verify the pipeline.

## Prerequisites
- GitLab project with CI/CD enabled.
- AWS IAM user/role with permissions: ECR (login/push), EKS (update-kubeconfig/apply), Secrets Manager (read), CloudFormation (describe), STS (get-caller-identity).
- EKS auth: the IAM principal must be mapped in the cluster’s `aws-auth` configmap.

## Required CI/CD Variables
Add these in GitLab → Settings → CI/CD → Variables (mask + protect):
- `AWS_ACCESS_KEY_ID`
+- `AWS_SECRET_ACCESS_KEY`
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
Optional overrides (defaults shown): `AWS_REGION` (`us-east-1`), `STACK_NAME` (`co-intelligence`), `EKS_CLUSTER_NAME` (`co-intelligence-cluster`), `IMAGE_TAG` (timestamp).

## Pipeline Overview
File: `.gitlab-ci.yml`
- Image: `docker:27.3.1` with `docker:dind` service.
- Installs: AWS CLI, kubectl, jq, curl.
- Stage: `deploy`
- Trigger: branch `main` (adjust in `rules` if needed).
- Script: `bash deploy.sh`

## Runner Requirements
- Docker executor with DinD and privileged enabled (GitLab shared runners support this).
- Network egress to AWS APIs and your ECR/EKS endpoints.

## How It Works
1) CI pulls the repo and installs tooling.
2) `deploy.sh`:
   - Validates AWS creds.
   - Reads CloudFormation outputs (ECR URIs, RDS endpoint, S3 bucket, Lambda ARN).
   - Fetches secrets from Secrets Manager.
   - Builds/pushes backend and frontend images to ECR.
   - Applies Kubernetes manifests to EKS (secrets, deployments, services).

## First Run Checklist
- Confirm `deploy.sh` is executable and committed.
- Push to `main` and watch the job log.
- If kubectl auth fails, update EKS `aws-auth` for your IAM principal.
- If ECR push fails, expand IAM permissions to include ECR actions.
- If Secrets Manager reads fail, ensure the two secrets exist:
  - `co-intelligence-secrets` (contains DB password key `password` or `DB_PASSWORD`)
  - `co-intelligence-secret-key`

## Customizing
- To deploy from another branch: change the `rules` in `.gitlab-ci.yml`.
- To add staging: duplicate the deploy job with a different `STACK_NAME`/`EKS_CLUSTER_NAME`/`IMAGE_TAG` and branch rule.

## Useful Commands (local)
```bash
aws sts get-caller-identity
aws eks update-kubeconfig --name co-intelligence-cluster --region us-east-1
kubectl get nodes
docker info
```
