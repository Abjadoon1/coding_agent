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


def build_repo_index(repo_files):
    file_codes = []

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


def build_module_map(repo_path, repo_files):
    project_modules = {
        ".".join(file_path.relative_to(repo_path).with_suffix("").parts): file_path
        for file_path in repo_files
        if file_path.suffix == ".py"
    }

    return project_modules


def build_dependency_map(repo_index, module_map):
    dependency_map = {}
    for repo_details in repo_index:
        dependencies = []
        for import_name in repo_details["imports"]:
            if import_name in module_map:
                dependencies.append(module_map[import_name])
        dependency_map[repo_details["path"]] = dependencies

    return dependency_map


def build_relationship_graph(repo_path):
    repo_files = scan_repo(repo_path)
    repo_index = build_repo_index(repo_files)
    module_map = build_module_map(repo_path, repo_files)
    dependency_map = build_dependency_map(repo_index, module_map)

    relationship_graph = []

    for repo_details in repo_index:
        current_file = repo_details["path"]
        used_by = []

        for file_path, dependencies in dependency_map.items():
            if current_file in dependencies:
                used_by.append(file_path)

        file_details = {
            "path": current_file,
            "functions": repo_details["functions"],
            "classes": repo_details["classes"],
            "internal_dependencies": dependency_map[current_file],
            "used_by": used_by,
        }

        relationship_graph.append(file_details)

    return relationship_graph


repo_path = ""

relationship_graph = build_relationship_graph(repo_path)

for file in relationship_graph:
    print("\nFILE:", file["path"])
    print("FUNCTIONS:", file["functions"])
    print("CLASSES:", file["classes"])
    print("DEPENDS ON:", file["internal_dependencies"])
    print("USED BY:", file["used_by"])
