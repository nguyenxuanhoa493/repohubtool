import re

# Fix yt.py
with open("files/yt.py", "r", encoding="utf-8") as f:
    yt_content = f.read()

yt_content = yt_content.replace("import ssl", "# import ssl")

with open("files/yt.py", "w", encoding="utf-8") as f:
    f.write(yt_content)

# Fix gameweb.py
with open("files/gameweb.py", "r", encoding="utf-8") as f:
    gw_content = f.read()

gw_content = gw_content.replace("import ssl", "# import ssl")
gw_content = gw_content.replace("_SSL_CONTEXT = ssl.create_default_context()", "_SSL_CONTEXT = None")
gw_content = gw_content.replace("_SSL_CONTEXT.check_hostname = False", "")
gw_content = gw_content.replace("_SSL_CONTEXT.verify_mode = ssl.CERT_NONE", "")

with open("files/gameweb.py", "w", encoding="utf-8") as f:
    f.write(gw_content)

print("Removed ssl imports!")
