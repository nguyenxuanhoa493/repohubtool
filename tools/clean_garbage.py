with open("files/gameweb.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    # If we see the broken button start, we skip until the end of that block
    if '<button class="btn btn-green" onclick="toggleScreenStream()" style="padding:12px 28px;' in line:
        skip = True
        
    if skip and '<!-- TAB 5: QUẢN LÝ FILE TRÊN THẺ NHỚ (FILE MANAGER) -->' in line:
        # Stop skipping, keep this line
        skip = False
        
    if not skip:
        new_lines.append(line)

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Cleaned up garbage HTML!")
