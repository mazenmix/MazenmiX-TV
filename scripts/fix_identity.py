#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "StreamVault-src")

# Keep the exact package identity of the original MazenmiX TV / MX TV APK.
# Debug normally adds .debug which causes Android to install a second app.
gradle = root / "app/build.gradle.kts"
text = gradle.read_text(encoding="utf-8")
text = text.replace('            applicationIdSuffix = ".debug"\n', '')
# Keep the build distinguishable internally, without changing package identity.
text = text.replace('            versionNameSuffix = "-debug"\n', '            versionNameSuffix = "-mxfast"\n')
gradle.write_text(text, encoding="utf-8")

# The original launcher label is MX TV. Force it in every values locale so no
# locale/debug resource can accidentally rename the launcher app.
for strings in (root / "app/src").glob("**/values*/strings.xml"):
    data = strings.read_text(encoding="utf-8")
    if 'name="app_name"' in data:
        data = re.sub(
            r'(<string\s+name="app_name"[^>]*>).*?(</string>)',
            r'\1MX TV\2',
            data,
            flags=re.DOTALL,
        )
        strings.write_text(data, encoding="utf-8")

print("identity fixed: package com.streamvault.app, launcher label MX TV")
