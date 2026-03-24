import os
import hashlib
import requests
import redis
from openai import OpenAI

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("PR_NUMBER")

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
    lines = diff.splitlines()

    image_line = None
    for line in lines:
        if "image:" in line:
            image_line = line.strip()
            break

    if image_line and ":latest" in image_line:
        fixed_image = image_line.replace(":latest", ":<version>")
        issues.append(f"""❌ Critical: Avoid using 'latest' tag
                       Fix: 
                      {fixed_image}
                      """)

    if "resources:" not in diff:
        issues.append("""⚠️ Warning: No resource limits defined
        Suggested block:
            resources:
            limits:
                cpu: "500m"
                memory: "256Mi" """)

    port = "80"
    for line in lines:
        if "containerPort" in line:
            port = line.split(":")[-1].strip()

    if "livenessProbe" not in diff and "readinessProbe" not in diff:
        issues.append(f"""
                **Warning**: No health checks defined
                Suggested block:
                livenessProbe:
                httpGet:
                    path: /
                    port: {port}
                """)
    if "privileged: true" in diff:
            issues.append("""
                    **Critical**: Privileged container detected

                    Recommendation:
                    Remove privileged: true unless strictly necessary
                    """)
            
    if "namespace:" not in diff:
        issues.append("""
                **Suggestion**: No namespace specified

                Consider defining a namespace for better isolation
                """)
    for line in lines:
        if "apiVersion" in line and "beta" in line:
            issues.append(f"""
                    **Warning**: Deprecated API version detected

                    Found:
                    {line.strip()}

                    Fix:
                    Use a stable version like apiVersion: apps/v1
                    """)
    if not issues:
        return "✅ No major issues detected."

    summary = f"## 📊 Summary\nFound {len(issues)} potential issues\n"
    return summary + "\n".join(issues)

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

    response = requests.post(url, headers=headers, json={"body": comment})

    print("POST Status:", response.status_code)
    print("POST Response:", response.text)

    redis_client.set(redis_key, "done", ex=3600)

    print("Review posted.")

finally:
    redis_client.close()
    print("Redis connection closed.")