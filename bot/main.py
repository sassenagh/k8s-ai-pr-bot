import os
import hashlib
import requests
import redis
from openai import OpenAI

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("GITHUB_REF").split("/")[-2]

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

client = OpenAI(api_key=OPENAI_API_KEY)


def fallback_review(diff: str) -> str:
    issues = []

    if "image:" in diff and ":latest" in diff:
        issues.append("❌ Critical: Avoid using 'latest' tag in images")

    if "resources:" not in diff:
        issues.append("⚠️ Warning: No resource limits defined")

    if "livenessProbe" not in diff and "readinessProbe" not in diff:
        issues.append("⚠️ Warning: No health checks defined")

    if not issues:
        return "✅ No major issues detected."

    return "\n".join(issues)

try:
    with open("diff.txt", "r") as f:
        diff = f.read()

    if not diff.strip():
        print("No changes detected.")
        exit(0)

    diff_hash = hashlib.sha256(diff.encode()).hexdigest()
    redis_key = f"pr_review:{PR_NUMBER}:{diff_hash}"

    if redis_client.exists(redis_key):
        print("Already reviewed, skipping...")
        exit(0)

    try:
        print("Trying OpenAI review...")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a Kubernetes expert reviewer."
                },
                {
                    "role": "user",
                    "content": f"""
                    Review this Kubernetes PR diff.

                    Identify:
                    - Critical issues
                    - Warnings
                    - Improvements

                    Suggest fixes in YAML.

                    Be concise and structured.

                    Diff:
                    {diff}
                    """
                }
            ],
        )

        review = response.choices[0].message.content

    except Exception as e:
        print(f"OpenAI failed: {e}")
        print("Using fallback review...")

        review = fallback_review(diff)

    comment = f"""
                ## Kubernetes Review

                {review}
                """

    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    requests.post(url, headers=headers, json={"body": comment})

    redis_client.set(redis_key, "done", ex=3600)

    print("Review posted.")

finally:
    redis_client.close()
    print("Redis connection closed.")