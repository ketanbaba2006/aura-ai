import re

def extract_files_from_llm_output(text: str) -> dict:
    files = {}

    # 1. Primary explicit tag: <<<FILE:name>>>...<<<END_FILE>>>
    file_tag_regex = re.compile(r"<<<FILE:([a-zA-Z0-9_\-\.\/]+)>>>([\s\S]*?)(?:<<<END_FILE>>>|(?=<<<FILE:)|$)")
    for match in file_tag_regex.finditer(text):
        fname = match.group(1).strip()
        fcontent = match.group(2).strip()
        fcontent = re.sub(r'^```[a-zA-Z0-9_\-]*\r?\n', '', fcontent)
        fcontent = re.sub(r'\r?\n```\s*$', '', fcontent)
        fcontent = re.sub(r'<<<END_FILE>>>\s*$', '', fcontent).strip()
        if fname and fcontent:
            files[fname] = fcontent

    if len(files) >= 1:
        return files

    # 2. Markdown sections with filenames before fences
    # Strip thinking chain if present (e.g., <thought>...</thought> or leading thoughts)
    clean_text = text
    if "</thought>" in clean_text:
        clean_text = clean_text.split("</thought>")[-1]

    code_blocks = list(re.finditer(r"```([a-zA-Z0-9_\-]+)?\s*\n([\s\S]*?)\n```", clean_text))
    prev_end = 0

    for block in code_blocks:
        start_idx = block.start()
        lang = (block.group(1) or "").lower().strip()
        content = block.group(2).strip()

        between_text = clean_text[prev_end:start_idx]
        prev_end = block.end()

        file_candidates = list(re.finditer(r"[`'\"]?([a-zA-Z0-9_\-\.]+\.(?:html|css|js|ts|json|py|jsx|tsx))[`'\"]?", between_text))
        
        fname = None
        for cand in reversed(file_candidates):
            candidate_name = cand.group(1).strip()
            if candidate_name.lower() not in ("three.js", "react.js", "vue.js", "node.js", "next.js", "orbitcontrols.js"):
                fname = candidate_name
                break
        
        if fname:
            files[fname] = content
        else:
            if (lang in ("html", "htm") or "<!doctype html" in content.lower()) and "index.html" not in files:
                files["index.html"] = content
            elif lang in ("css",) and "style.css" not in files:
                files["style.css"] = content
            elif lang in ("js", "javascript", "ts", "typescript") and "app.js" not in files:
                files["app.js"] = content
            elif lang in ("json",) and "data.json" not in files:
                files["data.json"] = content

    return files
