#! /usr/bin/env nix-shell
#! nix-shell shell.nix -i bash
# SPDX-FileCopyrightText: 2021 Oxhead Alpha
# SPDX-License-Identifier: LicenseRef-MIT-OA

# This script fetches the latest tag from the https://gitlab.com/tezos/tezos/ repository,
# compares it with the version presented in the nix/nix/sources.json, and performs an
# update if the versions are different

set -e

git config user.name "serokell-bot" # necessary for pushing
git config user.email "tezos-packaging@serokell.io"
git fetch --all

# Get latest tag from tezos/tezos
git clone https://gitlab.com/tezos/tezos.git upstream-repo
cd upstream-repo
latest_upstream_tag_hash="$(git rev-list --tags --max-count=1)"
latest_upstream_tag="$(git describe --tags "$latest_upstream_tag_hash")"
opam_repository_tag='' # will be set by version.sh
git checkout "$latest_upstream_tag"
source scripts/version.sh
cd ..
rm -rf upstream-repo

git clone --bare https://gitlab.com/tezos/opam-repository.git upstream-opam-repository
opam_repository_branch="$(git --git-dir=upstream-opam-repository for-each-ref --contains "$opam_repository_tag" --count=1 --sort='-refname' --format="%(refname:short)" refs/)"
rm -rf upstream-opam-repository

branch_name="auto/$latest_upstream_tag-release"

our_tezos_tag="$(jq -r '.tezos.ref' nix/nix/sources.json | cut -d'/' -f3)"

if [[ "$latest_upstream_tag" != "$our_tezos_tag" ]]; then
  # If corresponding branch doesn't exist yet, then the release PR
  # wasn't created
  if ! git rev-parse --verify "$branch_name"; then
    git switch -c "$branch_name"
    echo "Updating Tezos to $latest_upstream_tag"

    cd nix
    niv update tezos -a ref="refs/tags/$latest_upstream_tag" -a rev="$latest_upstream_tag_hash"
    niv update opam-repository -a rev="$opam_repository_tag" -a ref="$opam_repository_branch" -b "$opam_repository_branch"
    git commit -a -m "[Chore] Bump Tezos sources to $latest_upstream_tag" --gpg-sign="tezos-packaging@serokell.io"

    cd ..
    ./scripts/update-brew-formulae.sh "$latest_upstream_tag-1"
    git commit -a -m "[Chore] Update brew formulae for $latest_upstream_tag" --gpg-sign="tezos-packaging@serokell.io"

    sed -i 's/"release": "[0-9]\+"/"release": "1"/' ./meta.json
    # Commit may fail when release number wasn't updated since the last release
    git commit -a -m "[Chore] Reset release number for $latest_upstream_tag" --gpg-sign="tezos-packaging@serokell.io" || \
      echo "release number wasn't updated"

    git push --set-upstream origin "$branch_name"

    gh pr create -B master -t "[Chore] $latest_upstream_tag release" -F .github/release_pull_request_template.md
  fi
else
  echo "Our version is the same as the latest tag in the upstream repository"
fi
