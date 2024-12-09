# Super Productivity Webdav API
This is a Python package that allows you to interact with a WebDAV server to manage tasks for [Super Productivity](https://super-productivity.com/).

## Features
- Currently only supports adding tasks.
- Handle ETag changes to avoid conflicts.
- Uses Basic Auth to authenticate to the webdav server.

## Installation
Install using pip:
```
pip install super-productivity-webdav-api
```

## Requirements
- A WebDAV server to which Super Productivity is syncing

## Usage:

```
from super_productivity_webdav_api.client import Client

# Initialize the client
client = Client(
    url="https://your-webdav-server.com",
    username="your-username",
    password="your-password",
    remote_path="/super-productivity/"
)

# Add a task
client.add_task("My New Task")
```

- By default the tasks are added to your Inbox (with projectId "INBOX").
- Remote path is the folder in which your `MAIN.json` lives. Do not include the filename.

Adding tasks to another project should be possible, you will have to find the projectId in the JSON file and add it as an arg to `add_task`
