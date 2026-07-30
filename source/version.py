"""The one place the release version is declared.

Everything that states a version reads it from here: the build, the release
validator, the packager, the factsheet, the proofs, and `package.json`. It used to
live in four independent copies, which is how the specimen ended up advertising a
download for a release that was four versions old and did not exist.

`source/validate.py` asserts that no stale version string survives anywhere.
"""

VERSION = "1.000"

# package.json wants three components.
PACKAGE_VERSION = "1.0.0"

# The release archive the specimen links to.
ARCHIVE_NAME = f"FractalMono-v{VERSION}.zip"
