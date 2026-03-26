#!/usr/bin/env bash
set -e

VERSION=$(grep -m1 'version = "' pyproject.toml | sed 's/.*version = "\(.*\)".*/\1/')
MAJOR=$(echo "$VERSION" | cut -d. -f1)
MINOR=$(echo "$VERSION" | cut -d. -f2)
PATCH=$(echo "$VERSION" | cut -d. -f3)
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="$MAJOR.$MINOR.$NEW_PATCH"

echo "Bumping version: $VERSION → $NEW_VERSION"

sed -i "s/version = \"$VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

git add -A
git commit -m "Bump version to $NEW_VERSION"
git push
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
git push origin "v$NEW_VERSION"

echo "Released v$NEW_VERSION"