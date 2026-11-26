import os
import re

files = [
    "src/context/NotificationContext.tsx",
    "src/components/sidebar/Sidebar.tsx",
    "src/components/chat/Orb.tsx",
    "src/components/chat/AuraAvatar.tsx",
    "src/components/chat/ChatWindow.tsx",
    "src/components/chat/ActionMenu.tsx",
    "src/components/chat/StatusBadge.tsx",
    "src/components/chat/MessageBubble.tsx",
    "src/components/chat/actions/CameraCapture.tsx",
    "src/components/chat/actions/AudioRecorder.tsx",
    "src/components/chat/ChatInput.tsx",
    "src/components/auth/LoginScreen.tsx",
    "src/components/layout/AppShell.tsx",
    "src/components/pages/SettingsPage.tsx",
    "src/components/pages/FilesPage.tsx"
]

def remove_props(text):
    # Props to remove
    props = ['initial', 'animate', 'exit', 'transition', 'whileHover', 'whileTap', 'layout', 'layoutId', 'variants', 'custom']
    
    # We will do a basic regex that tries to remove these props.
    # It might not perfectly handle deeply nested braces, but we can try.
    for prop in props:
        # Match prop={...} or prop="..."
        # The value inside {} might contain nested braces, this is a simplified regex.
        # It matches prop={ followed by non-braces or a single level of braces }
        pattern1 = r'\s+' + prop + r'=(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|".*?"|\'.*?\')'
        text = re.sub(pattern1, '', text, flags=re.DOTALL)
        # Also remove prop={...} that might span multiple lines
        # A bit risky, but let's try a non-greedy match up to the matching brace.
    return text

for file in files:
    if not os.path.exists(file): continue
    with open(file, 'r') as f:
        content = f.read()
    
    # Remove imports
    content = re.sub(r'import\s+\{.*motion.*\}\s+from\s+["\']framer-motion["\'];?\n?', '', content)
    
    # Remove AnimatePresence wrapper (it might have props)
    content = re.sub(r'<\s*AnimatePresence[^>]*>', '', content)
    content = re.sub(r'<\s*/\s*AnimatePresence\s*>', '', content)
    
    # Replace motion.tag with tag
    content = re.sub(r'<\s*motion\.([a-zA-Z0-9_]+)', r'<\1', content)
    content = re.sub(r'<\s*/\s*motion\.([a-zA-Z0-9_]+)', r'</\1', content)
    
    # Remove animation props
    content = remove_props(content)
    
    with open(file, 'w') as f:
        f.write(content)

print("Done")
