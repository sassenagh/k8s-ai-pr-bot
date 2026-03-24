# AI Kubernetes PR Bot

![Python](https://img.shields.io/badge/python-3.11-blue)
![Docker](https://img.shields.io/badge/docker-containerized-blue)
![Kubernetes](https://img.shields.io/badge/kubernetes-native-blue)
![Redis](https://img.shields.io/badge/redis-storage-orange)
![OpenAI](https://img.shields.io/badge/OpenAI-integrated-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

A GitHub Actions bot that automatically reviews Kubernetes PRs, suggesting improvements and detecting potential issues.  

This project demonstrates a lightweight DevOps workflow including containerization, automated PR reviews, and caching with Redis.

Repository:  
https://github.com/sassenagh/k8s-ai-pr-bot

---

# Architecture

The bot runs as a containerized service triggered by GitHub Actions. It reads PR diffs and posts review comments. Redis is used for caching to avoid duplicate reviews.

```
   GitHub Pull Request
           │
           ▼
   GitHub Actions Workflow
           │
           ▼
    Docker Bot Container
   ┌───────────────┐
   │   Redis Cache │
   └───────────────┘
           │
           ▼
   GitHub PR Comments
```

Deployment workflow:

```
GitHub → CI/CD → Docker Image → GitHub Actions → PR Comment
```

---

# Features

- Automatic review of Kubernetes PR diffs using **OpenAI GPT-3.5** (optional)
- Detection of critical issues (privileged containers, `:latest` images)  
- Suggestions for improvements (resource limits, health checks, namespace, deprecated APIs)  
- Fallback review if OpenAI is not configured or quota is exhausted  
- Caching with Redis to avoid duplicate reviews  
- Containerized with Docker  
- Runs fully inside GitHub Actions  
- Logs review results and timestamps in PR comments  

---

# Tech Stack

## Backend

- Python 3.11
- Requests
- Redis-py
- **OpenAI API** (optional, fallback if unavailable)

## Infrastructure

- Docker
- Kubernetes native manifests

## CI/CD

- GitHub Actions

---

# Project Structure

```
k8s-ai-pr-bot
│
├── bot
│   └── main.py # PR review bot logic
│
├── Dockerfile
├── requirements.txt
└── README.md
```


---

# How It Works

1. GitHub Action is triggered on PRs affecting `k8s/**`.  
2. The workflow builds the Docker bot and a Redis container.  
3. Bot reads the PR diff and checks Redis cache.  
4. If not cached, bot runs a review:
   - Uses OpenAI if available
   - Falls back to rule-based review otherwise  
5. Posts structured comment on the PR  
6. Stores the diff hash in Redis to avoid duplicate reviews  

---

# Running Locally

Clone the repository:

```bash
git clone https://github.com/sassenagh/k8s-ai-pr-bot.git
cd k8s-ai-pr-bot
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the bot manually:

```bash
docker network create mynet || true
docker run -d --name redis --network mynet redis:7
docker build -t k8s-ai-pr-bot .
docker run --rm
--network mynet
-e GITHUB_TOKEN=<your_token>
-e GITHUB_REPOSITORY=<user/repo>
-e PR_NUMBER=<PR_number>
-e REDIS_HOST=redis
-e REDIS_PORT=6379
-v $PWD:/app
k8s-ai-pr-bot
```

---

# GitHub Actions Workflow

- Triggered on PRs with changes in `k8s/**`  
- Builds Docker bot image  
- Runs Redis container  
- Executes bot and posts PR comment  

Example workflow snippet:
```
on:
pull_request:
types: [opened, synchronize, reopened]
paths:
- "k8s/**"
```

---

# Future Improvements

- Use OpenAI GPT-4 / turbo for advanced PR suggestions  
- More dynamic rule-based analysis (e.g., detect RBAC misconfigurations)  
- Support multiple PRs concurrently  
- Add CI/CD notifications or Slack integration  
- Helm chart for deployment  

---

# License

MIT License