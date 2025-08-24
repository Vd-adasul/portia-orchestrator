# api/tools/github.py
import os
from github import Github
from portia_sdk.tool import Tool

# --- API KEY USAGE ---
# This file uses the following environment variable:
# - GITHUB_TOKEN: For connecting to the GitHub API.

# --- GitHub API Setup ---
try:
    g = Github(os.environ["GITHUB_TOKEN"])
    user = g.get_user()
except Exception as e:
    print(f"Error initializing GitHub client: {e}")
    g = None
    user = None

# --- Live Tools ---
def fetch_github_items_func():
    if not g or not user: return "GitHub client not initialized."
    query = f'assignee:{user.login} is:open'
    items = []
    for item in g.search_issues(query):
        items.append({
            "id": f"github-{item.number}", "type": "PR" if item.pull_request else "Issue",
            "title": item.title, "url": item.html_url, "repo": item.repository.full_name, "number": item.number
        })
    return items

def post_github_comment_func(repo_name: str, issue_number: int, comment: str):
    if not g: return "GitHub client not initialized."
    try:
        g.get_repo(repo_name).get_issue(number=issue_number).create_comment(comment)
        return f"Successfully posted comment to {repo_name}#{issue_number}."
    except Exception as e: return f"Error posting comment: {e}"

def merge_pull_request_func(repo_name: str, pr_number: int, merge_method: str = "merge"):
    if not g: return "GitHub client not initialized."
    try:
        pr = g.get_repo(repo_name).get_pull(pr_number)
        if pr.mergeable:
            pr.merge(merge_method=merge_method)
            return f"Successfully merged PR #{pr_number} in {repo_name}."
        return f"Error: PR #{pr_number} in {repo_name} is not mergeable."
    except Exception as e: return f"Error merging PR: {e}"

# --- Tool Definitions ---
fetch_github_items = Tool(id="fetch_github_items", func=fetch_github_items_func, description="Fetches all open pull requests and issues assigned to the current user.")
post_github_comment = Tool(id="post_github_comment", func=post_github_comment_func, description="Posts a comment to a GitHub issue or pull request.")
merge_pull_request = Tool(id="merge_pull_request", func=merge_pull_request_func, description="Merges a pull request.")
github_tools = [fetch_github_items, post_github_comment, merge_pull_request]
