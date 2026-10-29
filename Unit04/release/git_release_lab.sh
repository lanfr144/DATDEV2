#!/usr/bin/env bash
# =============================================================================
# DEVOP2 Unit 04b (Release Management Lab) + Unit 05 (Git rollbacks), replayed
# on the Book&Ride rentals service, in a THROW-AWAY repository.
#   ./release/git_release_lab.sh [directory]     (default: a new temp directory)
# Never touches a real repository. Output: docs/git_release_lab_output.txt
# =============================================================================
set -euo pipefail
UNIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LAB=${1:-$(mktemp -d)/release-strategies-lab}
OUT="$UNIT_DIR/docs/git_release_lab_output.txt"
run() { echo "\$ $*"; "$@"; }
step() { echo; echo "### $*"; }
{
step "Part 1 - semantic versioning (repository: $LAB)"
mkdir -p "$LAB"; cd "$LAB"
git init -q -b main .
git config user.name "Book&Ride CI"; git config user.email "ci@bookandride.example"
echo "# Book&Ride rentals service" > README.md
git add README.md; git commit -qm "Initial commit"
echo 'VERSION = "1.0.0"  # rentals: price_eur' > app.py
git add app.py; git commit -qm "feat: rentals service extracted from the monolith"
run git tag -a v1.0.0 -m "First release of the rentals service"
echo 'FEATURES = ["price_detail"]  # 1.1.0: optional field, backward compatible' >> app.py
git commit -qam "feat: add price_detail to POST /rentals/stop"
run git tag -a v1.1.0 -m "MINOR: new optional field"
printf 'VERSION = "2.0.0"\nFEATURES = ["price_detail", "price_cents"]  # price_eur removed\n' > app.py
git commit -qam "feat!: price_cents replaces price_eur (BREAKING CHANGE)"
run git tag -a v2.0.0 -m "MAJOR: breaking API change"
echo "Q: bug fix after v2.0.0 -> v2.0.1 (PATCH). New endpoint that changes nothing existing -> v2.1.0 (MINOR)."

step "Part 2 - tags and release notes"
run git tag -n1
cp "$UNIT_DIR/release/CHANGELOG.md" RELEASE_NOTES.md
git add RELEASE_NOTES.md; git commit -qm "docs: release notes v1.0.0 to v2.0.2"
head -12 RELEASE_NOTES.md

step "Part 3.1 - blue/green (branches)"
git checkout -qb blue;  echo "Blue version running (v1.1.0)" > deployment.txt
git add deployment.txt; git commit -qm "Blue: current production version"
git checkout -qb green; echo "Green version running (v2.0.0)" > deployment.txt
git commit -qam "Green: new version deployed and validated"
git checkout -q main; run git merge -q --no-edit green; run cat deployment.txt

step "Part 3.2 - rolling (3 servers, one batch at a time)"
mkdir -p server1 server2 server3
for s in 1 2 3; do echo "v1.1.0" > server$s/version.txt; done
git add .; git commit -qm "Initial state: 3 servers on v1.1.0"
for s in 1 2 3; do echo "v2.0.1" > server$s/version.txt; git commit -qam "Rolling update: server$s to v2.0.1"; done
run grep -H . server1/version.txt server2/version.txt server3/version.txt
run git tag -a v2.0.1 -m "PATCH: fix of v2.0.0 (v2.0.0 is never moved)"

step "Part 3.3 - canary"
echo "v2.1.0 (canary)" > server1/version.txt
git commit -qam "Canary: server1 runs v2.1.0 for 10% of traffic"
run git log --oneline --graph --all -n 12

step "Part 4 - rollback with revert (history kept)"
run git revert --no-edit HEAD
run cat server1/version.txt
run git log --oneline -n 3

step "Unit 05 - undo in the working directory / staging area"
echo "Temporary change" >> app.py; run git status --short
run git restore app.py;           run git status --short
echo "New feature" >> app.py; git add app.py
run git reset -q app.py;          run git status --short
git checkout -q -- app.py

step "Unit 05 - reset --soft / --mixed / --hard, then recover with reflog"
echo "SECRET=do-not-commit" >> app.py; git commit -qam "Add secret data (mistake)"
LOST=$(git rev-parse --short HEAD)
run git reset --soft HEAD~1;  run git status --short          # change kept, staged
git commit -qm "Add secret data (mistake)"
run git reset HEAD~1;         run git status --short          # change kept, unstaged
git commit -qam "Add secret data (mistake)"
run git reset --hard HEAD~1;  run git status --short          # change GONE
run git reflog -n 4
echo "commit $LOST is still in the reflog: git reset --hard $LOST would bring it back"
echo "(here we leave it out: a secret must never be pushed)"

step "Unit 05 - restore a deleted tracked file"
rm app.py; run git status --short; run git restore app.py; run ls app.py

step "Unit 05 - hotfix branch instead of resetting production"
git checkout -qb hotfix/2.0.2
echo "# 2.0.2: fix rounding of price_cents" >> app.py
git commit -qam "fix: rounding of price_cents"
git checkout -q main; run git merge -q --no-edit hotfix/2.0.2
run git tag -a v2.0.2 -m "PATCH: hotfix"
run git tag
run git log --oneline --graph --all -n 8
} 2>&1 | tee "$OUT"
echo "(output saved in $OUT; lab repository: $LAB)"
