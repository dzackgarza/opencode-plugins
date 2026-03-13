import os

path = os.path.expanduser("~/.zshrc")
with open(path, "r") as f:
    lines = f.readlines()

final_alias = "alias gh-issues='gh search issues --owner dzackgarza --state open --limit 50 --json title,url,repository,number --template \"{{range .}}{{.repository.name}}: #{{.number}} {{.title}} ({{.url}}){{\\\"\\n\\\"}}{{end}}\"'\n"
compatibility_alias = "alias linear-open='gh-issues'\n"

# Remove existing occurrences of both to avoid duplicates
filtered_lines = [l for l in lines if not l.startswith("alias gh-issues=") and not l.startswith("alias linear-open=")]

# Find where to insert (where the old l, la, ll aliases were)
insert_idx = -1
for i, line in enumerate(filtered_lines):
    if "alias ll=" in line or "alias la=" in line or "alias l=" in line:
        insert_idx = i + 1

if insert_idx != -1:
    filtered_lines.insert(insert_idx, final_alias)
    filtered_lines.insert(insert_idx + 1, compatibility_alias)
else:
    # If no markers found, just append
    filtered_lines.append(final_alias)
    filtered_lines.append(compatibility_alias)

with open(path, "w") as f:
    f.writelines(filtered_lines)
print("Updated aliases.")
