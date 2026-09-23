import os
from pathlib import Path
import ast

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
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)

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


def find_function(repo_index, function_name):
    for repo in repo_index:
        if function_name in repo["functions"]:
            return repo["path"]
    return None


def find_class(repo_index, class_name):
    for repo in repo_index:
        if class_name in repo["classes"]:
            return repo["path"]
    return None


def find_import(repo_index, import_name):
    for repo in repo_index:
        if import_name in repo["imports"]:
            return repo["path"]
    return None


print(build_repo_index("/opt/anaconda3/envs/coding_agent/Project/"))
