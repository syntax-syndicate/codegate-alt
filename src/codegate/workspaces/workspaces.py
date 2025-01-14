import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

from codegate.db.connection import DbRecorder
from codegate.db.models import Workspace


class Folder(BaseModel):
    files: List[str] = []


class Repository(BaseModel):
    name: str
    folder_tree: Dict[str, Folder]


class FolderRepoScanner:

    def __init__(self, ignore_paths: Optional[List[str]] = None):
        if ignore_paths is None:
            ignore_paths = []
        self.ignore_paths = ignore_paths

    def _should_skip(self, path: Path):
        """Skip certain paths that are not relevant for scanning."""
        return any(part in path.parts for part in self.ignore_paths)

    def _read_repository_structure(self, repo_path: Path) -> Dict[str, Folder]:
        folder_tree: Dict[str, Folder] = {}
        for path in repo_path.rglob('*'):
            if self._should_skip(path):
                continue

            relative_path = path.relative_to(repo_path)
            if path.is_dir():
                folder_tree[str(relative_path)] = Folder()
            else:
                parent_dir = str(relative_path.parent)
                if parent_dir not in folder_tree:
                    folder_tree[parent_dir] = Folder()
                folder_tree[parent_dir].files.append(path.name)
        return folder_tree

    def read(self, path_str: Union[str, Path]) -> List[Repository]:
        path_dir = Path(path_str)
        if not path_dir.is_dir():
            print(f"Path {path_dir} is not a directory")
            return []

        found_repos = []
        for child_path in path_dir.rglob('*'):
            if child_path.is_dir() and (child_path / ".git").exists():
                repo_structure = self._read_repository_structure(child_path)
                new_repo = Repository(name=child_path.name, folder_tree=repo_structure)
                found_repos.append(new_repo)
                print(f"Found repository at {child_path}.")

        return found_repos

class Workspaces:

    def __init__(self):
        self._db_recorder = DbRecorder()

    def read_workspaces(self, path: str, ignore_paths: Optional[List[str]] = None) -> None:
        repos = FolderRepoScanner(ignore_paths).read(path)
        workspaces = [
            Workspace(
                id=str(uuid.uuid4()),
                name=repo.name,
                folder_tree_json=json.dumps(repo.folder_tree)
            )
            for repo in repos
        ]
        asyncio.run(self._db_recorder.record_workspaces(workspaces))
