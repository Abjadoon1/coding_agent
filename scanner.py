import os
import ast
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}
valid_extensions = {
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}

valid_files = {
    "Dockerfile",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    ".dockerignore",
}


class RepoSearch(BaseModel):
    repo_paths: list[dict] = Field(default_factory=list)
    search_type: Literal["imports", "classes", "functions"]
    keyword: str


def scan_repo(repo_path):
    file_paths = []
    repo_path = Path(repo_path)
    if not repo_path.exists():
        raise FileNotFoundError(f"Repository doesn't exit: {repo_path}")
    if not repo_path.is_dir():
        raise NotADirectoryError(f"Repository path is not directory: {repo_path}")

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [dirname for dirname in dirs if dirname not in IGNORE_DIRS]
        files[:] = [
            filename
            for filename in files
            if Path(filename).suffix in valid_extensions or filename in valid_files
        ]
        current_repo = Path(root)
        for file in files:
            paths = current_repo / file
            file_paths.append(paths)
    return file_paths


def read_file(file_path):
    with open(file_path, "r") as file:
        code = file.read()
        tree = ast.parse(code)

        functions = []
        classes = []
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module)
            elif isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ClassDef):
                class_detail = {
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                }
                classes.append(class_detail)
            elif isinstance(node, ast.FunctionDef):
                function_detail = {
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                }
                functions.append(function_detail)

    return {
        "path": Path(file_path),
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


def build_repo_index(repo_path):
    file_codes = []
    repo_files = scan_repo(repo_path)
    code_files = [file for file in repo_files if file.suffix == ".py"]
    for file in code_files:
        code_details = read_file(file)
        file_codes.append(code_details)

    return file_codes


def search_repo(search: RepoSearch):
    for repo in search.repo_paths:
        if search.search_type == "imports":
            names = repo["imports"]
        else:
            names = [item["name"] for item in repo[search.search_type]]
        if search.keyword in names:
            return repo["path"]
    return None


def search_text(repo_files, keyword):
    results = []
    for repo_file in repo_files:
        with open(repo_file, "r") as file:
            for index, line in enumerate(file, start=1):
                clean_line = line.strip()
                if keyword in clean_line:
                    results.append(
                        {
                            "path": repo_file,
                            "line": index,
                            "text": clean_line,
                        }
                    )

    return results


repo_path = "/opt/anaconda3/envs/coding_agent/Project/"

repo_files = scan_repo(repo_path)
repo_index = build_repo_index(repo_path)
search_function = RepoSearch(
    repo_paths=repo_index,
    search_type="functions",
    keyword="search_text",
)

search_class = RepoSearch(
    repo_paths=repo_index,
    search_type="classes",
    keyword="RepoSearch",
)

search_import = RepoSearch(
    repo_paths=repo_index,
    search_type="imports",
    keyword="ast",
)

print(search_repo(search_function))
print(search_repo(search_class))
print(search_repo(search_import))
print(search_text(repo_files, "ast"))
