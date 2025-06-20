#!/bin/bash

# usage: ./make_gittar.sh [tarname]
# default: git_repo_YYYYMMDD.tar.gz

set -e

TARNAME="${1:-git_repo_$(date +%Y%m%d).tar.gz}"

# git tracked file gzip
git ls-files | tar -zcf "$TARNAME" -T -

echo "Created: $TARNAME"

open "$TARNAME" || echo "Failed to open $TARNAME. Please open it manually."