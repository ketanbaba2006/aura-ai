import re

with open('src/app/globals.css', 'r') as f:
    css = f.read()

# Remove animation: ... properties
css = re.sub(r'^\s*animation:.*?;[ \t]*\n?', '', css, flags=re.MULTILINE)

# Remove @keyframes blocks
# A simple brace-matching approach for CSS
def remove_keyframes(css_text):
    result = []
    i = 0
    while i < len(css_text):
        match = re.search(r'@keyframes', css_text[i:])
        if not match:
            result.append(css_text[i:])
            break
        
        start_idx = i + match.start()
        result.append(css_text[i:start_idx])
        
        # find the matching brace for @keyframes
        brace_level = 0
        in_keyframes = False
        j = start_idx
        while j < len(css_text):
            if css_text[j] == '{':
                brace_level += 1
                in_keyframes = True
            elif css_text[j] == '}':
                brace_level -= 1
                if in_keyframes and brace_level == 0:
                    j += 1
                    break
            j += 1
        
        i = j
        
    return "".join(result)

css = remove_keyframes(css)

with open('src/app/globals.css', 'w') as f:
    f.write(css)

print("Animations removed from CSS")
