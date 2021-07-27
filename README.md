<!--
   - SPDX-FileCopyrightText: 2019-2021 TQ Tezos <https://tqtezos.com/>
   -
   - SPDX-License-Identifier: LicenseRef-MIT-TQ
   -->

# Tezos packaging

[![Build status](https://badge.buildkite.com/e899e9e54babcd14139e3bd4381bad39b5d680e08e7b7766d4.svg?branch=master)](https://buildkite.com/serokell/tezos-packaging)

This repo provides various form of distribution for tezos-related executables:
* `tezos-client`
* `tezos-admin-client`
* `tezos-node`
* `tezos-baker`
* `tezos-accuser`
* `tezos-endorser`
* `tezos-signer`
* `tezos-codec`
* `tezos-sandbox`

Daemon binaries (as well as packages for them) have suffix that defines their target protocol,
e.g. `tezos-baker-010-PtGRANAD` can be used only on the chain with 010 protocol.

Other binaries can be used with all protocols if they're new enough. E.g.
010 protocol is supported only from `v9.2`. `tezos-node` can be set up to run
different networks, you can read more about this in [this article](https://tezos.gitlab.io/user/multinetwork.html).

## Table of contents

* [Installing Tezos](#installing-tezos).
* [Setting up a node and/or baking on Ubuntu](#baking-on-ubuntu).
* [Building instructions](#building).
* [Contribution](#contribution).
* [About Serokell](#about)

## Installing Tezos

`tezos-packaging` supports several native distribution methods for convenience:

- [**Ubuntu**](./docs/distros/ubuntu.md)
- [**Raspberry Pi OS**](./docs/distros/ubuntu.md#raspberry)
- [**Fedora**](./docs/distros/fedora.md)
- [**macOS**](./docs/distros/macos.md)

Additionally, prebuilt **static binaries** can be downloaded directly from the
[latest release](https://github.com/serokell/tezos-packaging/releases/latest)
for other linux distros.

You can also use `systemd` services to run some of these static Tezos binaries
in the background.
For more information about these services, refer to [this doc](./docs/systemd.md#generic-linux).

<a name="baking-on-ubuntu"></a>
## Setting up a node and/or baking on Ubuntu

Read [the article](./docs/baking.md) to find out an easy way to set up
baking instance on Ubuntu using packages provided by our launchpad PPA.

For ease of use, a CLI wizard is provided within the `tezos-baking` package, designed to query all
necessary configuration options and use the answers to automatically set up a baking instance.

To use it, install the `tezos-baking` package for Ubuntu and run `tezos-setup-wizard`.

<a name="building"></a>
## Build Instructions

This repository provides two distinct ways for building and packaging tezos binaries:
* [Docker-based](./docker/README.md)
* [Nix-based](./nix/README.md)

<a name="contribution"></a>
## For Contributors

Please see [CONTRIBUTING.md](.github/CONTRIBUTING.md) for more information.

<a name="about"></a>
## About Serokell

This repository is maintained with ❤️ by [Serokell](https://serokell.io/).
The names and logo for Serokell are trademark of Serokell OÜ.

We love open source software! See [our other projects](https://serokell.io/community?utm_source=github)
or [hire us](https://serokell.io/hire-us?utm_source=github) to design, develop and grow your idea!
