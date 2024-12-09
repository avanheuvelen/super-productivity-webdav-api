import os
import json
import time
import logging

from webdav4.client import Client as WebDAVClient
from nanoid import generate
from urllib.parse import urljoin
from tempfile import NamedTemporaryFile
from .exceptions import EtagChangedException

logger = logging.getLogger(__name__)

class Client:
    """Abstraction for interacting with the WebDAV remote and managing tasks."""

    def __init__(self, url, username, password, remote_path, temp_file=None):
        """
        Initialize the WebDAV client and set up paths.

        Args:
            url (str):          WebDAV server URL.
            username (str):     WebDAV username.
            password (str):     WebDAV password.
            remote_path (str):  Path to the remote JSON file (directory, not file).
        """
        self.webdav_client = WebDAVClient(base_url=url, auth=(username, password))

        self.remote_file = remote_path.strip('/') + '/MAIN.json'
        self.local_file = temp_file or NamedTemporaryFile(delete=False).name

    def _download_file_with_etag(self):
        """Downloads the file and returns its ETag."""
        logger.debug(f"Downloading file: {self.remote_file}")
        self.curr_etag = self.webdav_client.etag(self.remote_file)
        self.webdav_client.download_file(self.remote_file, self.local_file)

    def _verify_etag_unchanged(self):
        """Checks if the file's ETag has changed."""
        current_etag = self.webdav_client.etag(self.remote_file)
        if current_etag != self.curr_etag:
            logger.warning("ETag has changed. Aborting operation.")
            raise EtagChangedException

    def _upload_file(self):
        """Uploads the local file to the server."""
        logger.debug(f"Uploading file: {self.local_file} -> {self.remote_file}")
        self.webdav_client.upload_file(self.local_file, self.remote_file, overwrite=True)

    def _create_task_entry(self, task_text, project_id):
        task_id = generate()
        time_now = int(time.time() * 1000)
        return {
            "id": task_id,
            "projectId": project_id,
            "subTaskIds": [],
            "timeSpentOnDay": {},
            "timeSpent": 0,
            "timeEstimate": 0,
            "isDone": False,
            "doneOn": None,
            "title": task_text,
            "notes": "",
            "tagIds": [ ],
            "parentId": None,
            "reminderId": None,
            "created": time_now,
            "repeatCfgId": None,
            "plannedAt": None,
            "_showSubTasksMode": 2,
            "attachments": [],
            "issueId": None,
            "issueProviderId": None,
            "issuePoints": None,
            "issueType": None,
            "issueAttachmentNr": None,
            "issueLastUpdated": None,
            "issueWasUpdated": None,
            "issueTimeTracked": None
        }

    def _modify_json_file(self, task_text, project_id):
        """Modify the local JSON file to add the new task."""
        logger.debug("Modifying local JSON file.")

        with open(self.local_file, 'r+') as f:
            data = json.load(f)
            task = self._create_task_entry(task_text, project_id)

            data["task"]["entities"][task["id"]] = task
            data["task"]["ids"].append(task["id"])
            data["project"]["entities"][project_id]["taskIds"].append(task["id"])
            data["lastLocalSyncModelChange"] = task["created"]

            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()

    def add_task(self, task_text, project_id="INBOX", retries=3):
        """
        Add a task to Super Productivity

        Args:
            task_text (str):    The title of the task
            project_id (str):   The project name in Super Productivity
            retries (int):      Number of retries in case of failures.
        """
        logger.debug("Adding task to remote file.")
        success = False
        for attempt in range(1, retries + 1):
            try:
                self._download_file_with_etag()
                self._modify_json_file(task_text, project_id)
                self._verify_etag_unchanged()
                self._upload_file()
                success = True
                logger.info(f"Task added successfully.")
                break
            except EtagChangedException:
                logger.warning(f"ETag mismatch, retrying ({attempt}/{retries}).")
            except (json.JSONDecodeError, KeyError, IOError) as e:
                logger.error(f"Error modifying JSON file: {e}", exc_info=True)
            except Exception as e:
                logger.critical(f"Unexpected error: {e}", exc_info=True)
                continue
            finally:
                if os.path.exists(self.local_file):
                    logger.info("Cleaning up")
                    os.remove(self.local_file)
        if not success:
            logger.info("Failed to add task after multiple retries.")
