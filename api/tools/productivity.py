# api/tools/productivity.py
import os
from portia_sdk.tool import Tool
import notion_client

# --- API KEY USAGE ---
# This file uses the following environment variables:
# - NOTION_API_KEY: For connecting to the Notion API.
# - NOTION_DATABASE_ID: To specify which database to add tasks to.

# --- Notion API Setup ---
try:
    notion = notion_client.Client(auth=os.environ["NOTION_API_KEY"])
    NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
except Exception as e:
    print(f"Error initializing Notion client: {e}")
    notion = None

# --- Live Tool ---
def add_task_to_notion_db_func(task_title: str):
    if not notion: return "Notion client not initialized."
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={"Task": {"title": [{"text": {"content": task_title}}]}}
        )
        return f"Successfully added task '{task_title}' to Notion."
    except Exception as e: return f"Error adding task to Notion: {e}"

# --- Tool Definition ---
add_task_to_notion_db = Tool(id="add_task_to_notion_db", func=add_task_to_notion_db_func, description="Adds a new task to the user's primary Notion task database.")
productivity_tools = [add_task_to_notion_db]
