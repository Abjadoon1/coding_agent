import re
from pathlib import Path
from stop_words import get_stop_words
from pydantic import BaseModel, Field
from scanner import scan_repo, build_relationship_graph, search_text

ignore_words = set(get_stop_words("en"))


class ContextQuery(BaseModel):
    intent: str = Field(description="What the user is trying to find in the codebase")

    search_terms: list[str] = Field(
        description="Short code-related terms likely to appear in relevant files, functions, classes, imports, or source code"
    )


def retrieve_context(repo_path, query):
    words = [
        word
        for word in re.findall(r"\b\w+\b", query.lower())
        if word not in ignore_words
    ]

    if not words:
        return []

    repo_files = scan_repo(repo_path)
    relationship_graph = build_relationship_graph(repo_path)

    results = []

    for graph_obj in relationship_graph:
        score = 0
        reasons = []

        current_path = graph_obj["path"]

        for word in words:
            if word == current_path.stem.lower():
                score += 5
                reasons.append(f"filename matched: {word}")

            matched_classes = [
                item for item in graph_obj["classes"] if word == item["name"].lower()
            ]
            if matched_classes:
                score += len(matched_classes) * 4
                for item in matched_classes:
                    reasons.append(f"class matched: {item['name']}")

            matched_functions = [
                item for item in graph_obj["functions"] if word == item["name"].lower()
            ]
            if matched_functions:
                score += len(matched_functions) * 4

                for item in matched_functions:
                    reasons.append(f"function matched: {item['name']}")

            dependency_matches = [
                dependency
                for dependency in graph_obj["internal_dependencies"]
                if word == dependency.stem.lower()
            ]
            if dependency_matches:
                score += len(dependency_matches) * 3
                for dependency in dependency_matches:
                    reasons.append(f"dependency matched: {dependency.name}")

            text_results = search_text(repo_files, word)
            text_matches = [
                match for match in text_results if match["path"] == current_path
            ]
            if text_matches:
                text_score = min(len(text_matches), 3)
                score += text_score
                reasons.append(f"text matched '{word}': {len(text_matches)} times")

        if score > 0:
            results.append(
                {
                    "path": current_path,
                    "score": score,
                    "reasons": reasons,
                }
            )

    results.sort(
        key=lambda result: result["score"],
        reverse=True,
    )

    return results


def route_query(query, llm):
    structured_llm = llm.with_structured_output(ContextQuery)

    prompt = f"""
You are routing a user's question to a source-code search system.

Understand what the user is trying to find and generate useful search terms
that are likely to appear in the actual codebase.

Prefer code vocabulary such as:
- filenames
- function names
- class names
- module names
- technical implementation terms

Do not answer the user's question.
Only prepare the query for repository retrieval.

User question: {query}
"""
    return structured_llm.invoke(prompt)


repo_path = "/opt/anaconda3/envs/research_agent/projects"

results = retrieve_context(repo_path, "Where is database persistence implemented?")

for result in results:
    print("\nFILE:", result["path"])
    print("SCORE:", result["score"])

    for reason in result["reasons"]:
        print(" -", reason)
