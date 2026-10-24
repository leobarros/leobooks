#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-$(tr -d '[:space:]' < "$ROOT/VERSION")}"
mkdir -p "$ROOT/dist"
"$ROOT/packaging/build-source-tar.sh"

SPEC_DIR="$ROOT/build/rpm-spec"
rm -rf "$SPEC_DIR"
mkdir -p "$SPEC_DIR"
sed "s/__VERSION__/${VERSION}/g" "$ROOT/packaging/rpm/leobooks.spec" > "$SPEC_DIR/leobooks.spec"

# Fedora 42 é usado como ambiente de build; o RPM é x86_64 e autocontido.
docker run --rm \
  -v "$ROOT":/src:ro \
  -v "$ROOT/dist":/out \
  -v "$SPEC_DIR":/spec:ro \
  fedora:42 bash -lc '
    set -e
    dnf -y install rpm-build python3-devel python3-pip >/tmp/dnf.log
    mkdir -p /tmp/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
    cp /spec/leobooks.spec /tmp/rpmbuild/SPECS/
    cp /src/dist/leobooks-*.tar.gz /tmp/rpmbuild/SOURCES/
    rpmbuild -bb --define "_topdir /tmp/rpmbuild" /tmp/rpmbuild/SPECS/leobooks.spec
    cp /tmp/rpmbuild/RPMS/x86_64/*.rpm /out/
  '
echo "RPMs gerados em $ROOT/dist"
