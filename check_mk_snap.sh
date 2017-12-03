#!/bin/bash
set -e
echo "Creating GIT snapshot of Check_MK"
rm -rf check_mk
curl 'http://git.mathias-kettner.de/git/?p=check_mk.git;a=snapshot;h=HEAD;sf=tgz' | tar xzf - 
cd check_mk
CMK_VERSION=$(grep ^VERSION Makefile | sed 's/.*= *//').$(date +"%Y.%m.%d")
make NEW_VERSION=$CMK_VERSION setversion
make dist
git rm -f ../packages/check_mk/*.tar.gz || true
mv -v check_mk-$CMK_VERSION.tar.gz ../packages/check_mk
git add ../packages/check_mk/*.tar.gz
git rm -f ../packages/mk-livestatus/*.tar.gz || true
mv -v mk-livestatus-$CMK_VERSION.tar.gz ../packages/mk-livestatus
git add ../packages/mk-livestatus/*.tar.gz
cd ../packages/check_mk
sed -i "s/^VERSION =.*/VERSION = $CMK_VERSION/" Makefile
make upstream
git add Makefile skel/etc/check_mk/defaults
cd ../mk-livestatus
sed -i "s/^VERSION =.*/VERSION = $CMK_VERSION/" Makefile
make upstream
git add Makefile
cd ../..
OMD_VERSION=$(grep ^OMD_VERSION Makefile.omd | sed 's/.*= *//' | sed 's/\.cmk.*//').cmk.$CMK_VERSION
make VERSION=$OMD_VERSION version
git add Makefile.omd packages/omd/omd
rm -rf check_mk
echo "FERTIG. Sieht gut aus. Ich mache einen Commit"
git commit -m 'New GIT-snapshot of Check_MK'
