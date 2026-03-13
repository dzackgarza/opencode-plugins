import sys
import os

# Read the generated section from stdin
new_section = sys.stdin.read()
index_path = "/home/dzack/www/html/index.html"

try:
    with open(index_path, "r") as f:
        content = f.read()

    # Find the end of the dashboard div
    # In the provided HTML, there is a final </div> for the .dashboard container.
    # We want to insert our section just before that.
    
    # Let's count the </div> tags. The dashboard container is the last one to close.
    parts = content.split("</div>")
    if len(parts) > 1:
        # Join all but the last part, insert new section, then add the last part (</body> etc)
        # Wait, the structure is:
        # <div class="dashboard">
        #   ...
        #   <div class="services">...</div>
        # </div>
        # </body>
        
        # So we want to insert after the .services div but before the final .dashboard closing div.
        
        # Look for the last </div> before </body>
        insertion_point = content.rfind("</div>", 0, content.rfind("</body>"))
        if insertion_point != -1:
            updated_content = content[:insertion_point] + new_section + "\n        " + content[insertion_point:]
        else:
            # Fallback
            updated_content = content.replace("</body>", new_section + "\n</body>")
    else:
        updated_content = content.replace("</body>", new_section + "\n</body>")

    with open("index.html.tmp", "w") as f:
        f.write(updated_content)
    print("Successfully generated index.html.tmp")

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
