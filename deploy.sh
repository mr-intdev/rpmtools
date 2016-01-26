#!/bin/bash
# Script finalizes CHANGELOG for new release, creates tag and pushes it to git origin.
project_root=$1
new_rev=$2
cd $project_root
sed -i -e '1 s/^/\n\n\nv'"$new_rev"'\n=========\n\n/;' CHANGELOG.md
git commit BUILD.json CHANGELOG.md -m "Revision updated $new_rev";
git tag -a v$new_rev -m "Deploy tag";
git push origin master --tags;
