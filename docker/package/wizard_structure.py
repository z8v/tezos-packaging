# SPDX-FileCopyrightText: 2022 Oxhead Alpha
# SPDX-License-Identifier: LicenseRef-MIT-OA

"""
Contains shared code from all Tezos wizards for a command line wizard skeleton.

Helps with writing a tool that asks questions, validates answers, and executes
the appropriate steps using the final configuration.
"""

import os, sys, subprocess, shlex, shutil
import re, textwrap
import argparse
import urllib.request
import json

# Regexes

secret_key_regex = b"(encrypted|unencrypted):(?:\w{54}|\w{88})"
address_regex = b"tz[123]\w{33}"
protocol_hash_regex = (
    b"P[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]{50}"
)
signer_uri_regex = b"((?:tcp|unix|https|http):\/\/.+)\/(tz[123]\w{33})\/?"
ledger_regex = b"ledger:\/\/[\w\-]+\/[\w\-]+\/[\w']+\/[\w']+"
derivation_path_regex = b"(?:bip25519|ed25519|secp256k1|P-256)\/[0-9]+h\/[0-9]+h"


# Input validators


def enum_range_validator(options):
    def _validator(input):
        intrange = list(map(str, range(1, len(options) + 1)))
        if input not in intrange and input not in options:
            raise ValueError(
                "Please choose one of the provided values or use their respective numbers."
            )
        try:
            opt = int(input) - 1
        except:
            return input
        else:
            opts = options
            if isinstance(options, dict):
                opts = list(options.keys())
            return opts[opt]

    return _validator


def dirpath_validator(input):
    if input and not os.path.isdir(input):
        raise ValueError("Please input a valid path to a directory.")
    return input


def filepath_validator(input):
    if input and not os.path.isfile(input):
        raise ValueError("Please input a valid file path.")
    return input


def reachable_url_validator(suffix=None):
    def _validator(input):
        full_url = mk_full_url(input, suffix)
        if url_is_reachable(full_url):
            return input
        else:
            raise ValueError(f"{full_url} is unreachable. Please input a valid URL.")

    return _validator


def required_field_validator(input):
    if not input.strip():
        raise ValueError("Please provide this required option.")
    return input


# The input has to be valid to at least one of the two passed validators.
def or_validator(validator1, validator2):
    def _validator(input):
        try:
            return validator1(input)
        except:
            return validator2(input)

    return _validator


# Runs the input through the passed validator, allowing for possible alteration,
# but doesn't raise an exception if it doesn't validate to allow for custom options, too.
def or_custom_validator(validator):
    def _validator(input):
        result = input
        try:
            result = validator(input)
        except:
            pass
        return result

    return _validator


# To be validated, the input should adhere to the Tezos secret key format:
# {encrypted, unencrypted}:<base58 encoded string with length 54 or 88>
def secret_key_validator(input):
    match = re.match(secret_key_regex.decode("utf-8"), input.strip())
    if not bool(match):
        raise ValueError(
            "The input doesn't match the format for a Tezos secret key: "
            "{{encrypted, unencrypted}:<base58 encoded string with length 54 or 88>}"
            "\nPlease check the input and try again."
        )
    return input


# To be validated, the input should adhere to the derivation path format:
# [0-9]+h/[0-9]+h
def derivation_path_validator(input):
    derivation_path_regex_str = "[0-9]+h\/[0-9]+h"
    match = re.match(derivation_path_regex_str, input.strip())
    if not bool(match):
        raise ValueError(
            "The input doesn't match the format for a derivation path: "
            + derivation_path_regex_str
            + "\nPlease check the input and try again."
        )
    return input


# To be validated, the input should adhere to the signer URI format:
# (tcp|unix|https|http)://<host address>/tz[123]\w{33}
def signer_uri_validator(input):
    match = re.match(signer_uri_regex.decode("utf-8"), input.strip())
    if not bool(match):
        raise ValueError(
            "The input doesn't match the format for a remote signer URI: "
            + "(tcp|unix|https|http)://<host address>/<public key address>"
            + "\nPlease check the input and try again."
        )
    return input


# To be validated, the input should adhere to the protocol hash format:
# <base58 encoded string with length 51 starting with P>
def protocol_hash_validator(input):
    proto_hash_regex_str = protocol_hash_regex.decode("utf-8")
    match = re.match(proto_hash_regex_str, input.strip())
    if not bool(match):
        raise ValueError(
            "The input doesn't match the format for a protocol hash: "
            + proto_hash_regex_str
            + "\nPlease check the input and try again."
        )
    return input


class Validator:
    def __init__(self, validator):
        self.validator = validator

    def validate(self, input):
        if self.validator is not None:
            if isinstance(self.validator, list):
                for v in self.validator:
                    input = v(input)
                return input
            else:
                return self.validator(input)


# Command line argument parsing


parser = argparse.ArgumentParser()


# Utilities


def proc_call(cmd):
    return subprocess.check_call(shlex.split(cmd))


def get_proc_output(cmd):
    if sys.version_info.major == 3 and sys.version_info.minor < 7:
        return subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE)
    else:
        return subprocess.run(shlex.split(cmd), capture_output=True)


def progressbar_hook(chunk_number, chunk_size, total_size):
    done = chunk_number * chunk_size
    percent = min(int(done * 100 / total_size), 100)
    print("Progress:", percent, "%,", int(done / (1024 * 1024)), "MB", end="\r")


def color(input, colorcode):
    return colorcode + input + "\x1b[0m"


color_red = "\x1b[1;31m"


def yes_or_no(prompt, default=None):
    valid = False
    while not valid:
        answer = input(prompt).strip().lower()
        if not answer and default is not None:
            answer = default
        if answer in ["y", "yes"]:
            print()
            return True
        elif answer in ["n", "no"]:
            print()
            return False
        else:
            print(color("Please provide a 'yes' or 'no' answer.", color_red))


def mk_full_url(host_name, path):
    return "/".join([host_name.rstrip("/"), path.lstrip("/")])


def url_is_reachable(url):
    req = urllib.request.Request(url, headers=http_request_headers)
    try:
        urllib.request.urlopen(req)
        return True
    except (urllib.error.URLError, ValueError):
        return False


# Global options

key_import_modes = {
    "ledger": "From a ledger",
    "secret-key": "Either the unencrypted or password-encrypted secret key for your address",
    "remote": "Remote key governed by a signer running on a different machine",
    "json": "Faucet JSON file from https://teztnets.xyz/",
}

networks = {
    "mainnet": "Main Tezos network",
    "ithacanet": "Test network using version 012 of Tezos protocol (Ithaca2)",
    "jakartanet": "Test network using version 013 of Tezos protocol (Jakarta2)",
}

http_request_headers = {"User-Agent": "Mozilla/5.0"}

# Wizard CLI skeleton


suppress_warning_text = "TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER=YES"


def get_data_dir(network):
    output = get_proc_output("systemctl show tezos-node-" + network + ".service").stdout
    config = re.search(b"Environment=(.*)(?:$|\n)", output)
    if config is None:
        print(
            "tezos-node-" + network + ".service configuration not found, "
            "defaulting to /var/lib/tezos/node-" + network
        )
        return "/var/lib/tezos/node-" + network
    config = config.group(1)
    data_dir = re.search(b"DATA_DIR=(.*?)(?: |$|\n)", config)
    if data_dir is not None:
        return data_dir.group(1).decode("utf-8")
    else:
        print("DATA_DIR is undefined, defaulting to /var/lib/tezos/node-" + network)
        return "/var/lib/tezos/node-" + network


def get_key_address(tezos_client_options, key_alias):
    address = get_proc_output(
        f"sudo -u tezos {suppress_warning_text} tezos-client {tezos_client_options} "
        f"show address {key_alias} --show-secret"
    )
    if address.returncode == 0:
        value_regex = (
            b"(?:"
            + ledger_regex
            + b")|(?:"
            + secret_key_regex
            + b")|(?:remote\:"
            + address_regex
            + b")"
        )
        value = re.search(value_regex, address.stdout).group(0).decode()
        address = re.search(address_regex, address.stdout).group(0).decode()
        return (value, address)
    else:
        return None


def wait_for_ledger_app(ledger_app):
    output = b""
    try:
        while re.search(f"Found a Tezos {ledger_app}".encode(), output) is None:
            output = get_proc_output(
                f"sudo -u tezos {suppress_warning_text} tezos-client list connected ledgers"
            ).stdout
            proc_call("sleep 1")
    except KeyboardInterrupt:
        return None
    ledgers_derivations = {}
    for ledger_derivation in re.findall(ledger_regex, output):
        ledger_url = (
            re.search(b"ledger:\/\/[\w\-]+\/", ledger_derivation).group(0).decode()
        )
        derivation_path = (
            re.search(derivation_path_regex, ledger_derivation).group(0).decode()
        )
        ledgers_derivations.setdefault(ledger_url, []).append(derivation_path)
    return ledgers_derivations


def ledger_urls_info(ledgers_derivations, node_endpoint):
    ledgers_info = {}
    max_derivation_len = 0
    for derivations_paths in ledgers_derivations.values():
        max_derivation_len = max(max_derivation_len, max(map(len, derivations_paths)))
    for ledger_url, derivations_paths in ledgers_derivations.items():
        for derivation_path in derivations_paths:
            output = get_proc_output(
                f"sudo -u tezos {suppress_warning_text} tezos-client "
                f"show ledger {ledger_url + derivation_path}"
            ).stdout
            addr = re.search(address_regex, output).group(0).decode()
            balance = (
                get_proc_output(
                    f"sudo -u tezos {suppress_warning_text} tezos-client "
                    f"--endpoint {node_endpoint} get balance for {addr}"
                )
                .stdout.decode()
                .strip()
            )
            ledgers_info.setdefault(ledger_url, []).append(
                (
                    "{:" + str(max_derivation_len + 1) + "} address: {}, balance: {}"
                ).format(derivation_path + ",", addr, balance)
            )
    return ledgers_info


def search_baking_service_config(config_contents, regex, default):
    res = re.search(regex, config_contents)
    if res is None:
        return default
    else:
        return res.group(1)


def search_json_with_default(json_filepath, field, default):
    with open(json_filepath, "r") as f:
        try:
            json_dict = json.load(f)
        except:
            return default
        return json_dict.pop(field, default)


def replace_in_service_config(config_filepath, field, value):
    with open(config_filepath, "r") as f:
        config_contents = f.read()

    old = re.search(f"{field}=.*", config_contents)
    if old is None:
        return None
    else:
        new = f"{field}={value}"
        proc_call(f"sudo sed -i 's/{old.group(0)}/{new}' {config_filepath}")


class Step:
    def __init__(
        self,
        id: str,
        prompt: str,
        help: str,
        default: str = "1",
        options=None,
        validator=None,
    ):
        self.id = id
        self.prompt = prompt
        self.help = help
        self.default = default
        self.options = options
        self.validator = validator

    def pprint_options(self):
        i = 1
        def_i = None
        try:
            def_i = int(self.default)
        except:
            pass

        if self.options and isinstance(self.options, list):
            options_count = 0
            for o in self.options:
                if isinstance(o, dict):
                    for values in o.values():
                        if not isinstance(values, list):
                            options_count += 1
                        else:
                            options_count += len(values)
                else:
                    options_count += 1
            index_len = len(str(options_count))
            str_format = f"{{:{index_len}}}. {{}}"
            for o in self.options:
                if isinstance(o, dict):
                    for k, values in o.items():
                        print()
                        print(f"'{k}':")
                        print()
                        if not isinstance(values, list):
                            values = [values]
                        for v in values:
                            if def_i is not None and i == def_i:
                                print(str_format.format(i, "(default) " + v))
                            else:
                                print(str_format.format(i, v))
                            i += 1
                    print()
                else:
                    if def_i is not None and i == def_i:
                        print(str_format.format(i, "(default) " + o))
                    else:
                        print(str_format.format(i, o))
                    i += 1
        elif self.options and isinstance(self.options, dict):
            index_len = len(str(len(self.options)))
            max_option_len = max(map(len, self.options.keys()))
            padding = max(26, max_option_len + 2)
            indent_size = index_len + 4 + padding
            str_format = f"{{:{index_len}}}. {{:<{padding}}}  {{}}"
            for o in self.options:
                description = textwrap.indent(
                    textwrap.fill(self.options[o], 60),
                    " " * indent_size,
                ).lstrip()
                if def_i is not None and i == def_i:
                    print(str_format.format(i, o + " (default)", description))
                else:
                    print(str_format.format(i, o, description))
                i += 1
        elif not self.options and self.default is not None:
            print("Default:", self.default)


# Steps

secret_key_query = Step(
    id="secret_key",
    prompt="Provide either the unencrypted or password-encrypted secret key for your address.",
    help="The format is 'unencrypted:edsk...' for the unencrypted key, or 'encrypted:edesk...'"
    "for the encrypted key.",
    default=None,
    validator=Validator([required_field_validator, secret_key_validator]),
)

remote_signer_uri_query = Step(
    id="remote_signer_uri",
    prompt="Provide your remote key with the address of the signer.",
    help="The format is the address of your remote signer host, followed by a public key,\n"
    "i.e. something like http://127.0.0.1:6732/tz1V8fDHpHzN8RrZqiYCHaJM9EocsYZch5Cy\n"
    "The supported schemes are https, http, tcp, and unix.",
    default=None,
    validator=Validator([required_field_validator, signer_uri_validator]),
)

json_filepath_query = Step(
    id="json_filepath",
    prompt="Provide the path to your downloaded faucet JSON file.",
    help="Download the faucet JSON file from https://teztnets.xyz/.\n"
    "The file will contain the 'mnemonic' and 'secret' fields.",
    default=None,
    validator=Validator([required_field_validator, filepath_validator]),
)

derivation_path_query = Step(
    id="derivation_path",
    prompt="Provide derivation path for the key stored on the ledger.",
    help="The format is '[0-9]+h/[0-9]+h'",
    default=None,
    validator=Validator([required_field_validator, derivation_path_validator]),
)


def get_ledger_url_query(ledgers):
    return Step(
        id="ledger_url",
        prompt="Choose a ledger to get the new derivation from.",
        options=ledgers,
        default=None,
        validator=Validator([required_field_validator, enum_range_validator(ledgers)]),
        help="In order to specify new derivation path, you need to specify a ledger to get the derivation from.",
    )


# We define this step as a function since the corresponding step requires
# tezos-node to be running and bootstrapped in order to gather the data
# about the ledger-stored addresses, so it's called right before invoking
# after the node was boostrapped
def get_ledger_derivation_query(ledgers_derivations, node_endpoint):
    extra_options = ["Specify derivation path", "Go back"]
    full_ledger_urls = []
    for ledger_url, derivations_paths in ledgers_derivations.items():
        for derivation_path in derivations_paths:
            full_ledger_urls.append(ledger_url + derivation_path)
    return Step(
        id="ledger_derivation",
        prompt="Select a key to import from the ledger.\n"
        "You can choose one of the suggested derivations or provide your own:",
        help="'Specify derivation path' will ask a derivation path from you."
        "'Go back' will return you back to the key type choice.",
        default=None,
        options=[ledger_urls_info(ledgers_derivations, node_endpoint)] + extra_options,
        validator=Validator(
            [
                required_field_validator,
                enum_range_validator(full_ledger_urls + extra_options),
            ]
        ),
    )


class Setup:
    def __init__(self, config={}):
        self.config = config

    def query_step(self, step: Step):
        validated = False
        while not validated:
            print(step.prompt)
            step.pprint_options()
            answer = input("> ").strip()

            if answer.lower() in ["quit", "exit"]:
                raise KeyboardInterrupt
            elif answer.lower() in ["help", "?"]:
                print(step.help)
                print()
            else:
                if not answer and step.default is not None:
                    answer = step.default

                try:
                    if step.validator is not None:
                        answer = step.validator.validate(answer)
                except ValueError as e:
                    print(color("Validation error: " + str(e), color_red))
                else:
                    validated = True
                    self.config[step.id] = answer

    def systemctl_start_action(self, service):
        proc_call(
            f"sudo systemctl start tezos-{service}-{self.config['network']}.service"
        )

    def systemctl_enable(self):
        if self.config["systemd_mode"] == "yes":
            print(
                "Enabling the tezos-{}-{}.service".format(
                    self.config["mode"], self.config["network"]
                )
            )
            proc_call(
                f"sudo systemctl enable tezos-{self.config['mode']}-"
                f"{self.config['network']}.service"
            )
        else:
            print("The services won't restart on boot.")

    def get_tezos_client_options(self):
        options = (
            f"--base-dir {self.config['client_data_dir']} "
            f"--endpoint {self.config['node_rpc_addr']}"
        )
        if "remote_host" in self.config:
            options += f" -R '{self.config['remote_host']}'"
        return options

    def query_and_update_config(self, query):
        self.query_step(query)
        self.config["tezos_client_options"] = self.get_tezos_client_options()
        proc_call(
            f"sudo -u tezos {suppress_warning_text} tezos-client "
            f"{self.config['tezos_client_options']} config update"
        )

    def get_baking_config_filepath(self):
        net = self.config["network"]
        output = get_proc_output(f"systemctl show tezos-baking-{net}.service").stdout
        config_filepath = re.search(b"EnvironmentFiles=(.*) ", output)
        if config_filepath is None:
            print(
                f"EnvironmentFiles not found in tezos-baking-{net}.service configuration,",
                f"defaulting to /etc/default/tezos-baking-{net}",
            )
            config_filepath = f"/etc/default/tezos-baking-{net}"
        else:
            config_filepath = config_filepath.group(1).decode().strip()
        return config_filepath

    def fill_baking_config(self):
        config_filepath = self.get_baking_config_filepath()
        with open(config_filepath, "r") as f:
            config_contents = f.read()
            self.config["client_data_dir"] = search_baking_service_config(
                config_contents, 'DATA_DIR="(.*)"', "/var/lib/tezos/.tezos-client"
            )
            self.config["node_rpc_addr"] = search_baking_service_config(
                config_contents, 'NODE_RPC_ENDPOINT="(.*)"', "http://localhost:8732"
            )
            self.config["baker_alias"] = search_baking_service_config(
                config_contents, 'BAKER_ADDRESS_ALIAS="(.*)"', "baker"
            )

    def fill_remote_signer_infos(self):
        self.query_step(remote_signer_uri_query)

        rsu = re.search(signer_uri_regex.decode(), self.config["remote_signer_uri"])

        self.config["remote_host"] = rsu.group(1)
        self.config["remote_key"] = rsu.group(2)

    def get_current_head_level(self):
        response = urllib.request.urlopen(
            self.config["node_rpc_addr"] + "/chains/main/blocks/head/header"
        )
        return str(json.load(response)["level"])

    # Check if an account with the baker_alias alias already exists, and ask the user
    # if it can be overwritten.
    def check_baker_account(self):
        baker_alias = self.config["baker_alias"]
        baker_key_value = get_key_address(self.get_tezos_client_options(), baker_alias)
        if baker_key_value is not None:
            value, address = baker_key_value
            print()
            print("An account with the '" + baker_alias + "' alias already exists.")
            print("Its current value is", value)
            print("With a corresponding address:", address)

            return yes_or_no(
                "Would you like to import a new key and replace this one? <y/N> ", "no"
            )
        else:
            return True

    def import_key(self, key_mode_query, ledger_app=None):

        baker_alias = self.config["baker_alias"]
        tezos_client_options = self.get_tezos_client_options()

        valid_choice = False
        while not valid_choice:

            try:
                self.query_step(key_mode_query)

                if self.config["key_import_mode"] == "secret-key":
                    self.query_step(secret_key_query)
                    proc_call(
                        f"sudo -u tezos {suppress_warning_text} tezos-client {tezos_client_options} "
                        f"import secret key {baker_alias} {self.config['secret_key']} --force"
                    )
                elif self.config["key_import_mode"] == "remote":
                    self.fill_remote_signer_infos()

                    tezos_client_options = self.get_tezos_client_options()
                    proc_call(
                        f"sudo -u tezos {suppress_warning_text} tezos-client {tezos_client_options} "
                        f"import secret key {baker_alias} remote:{self.config['remote_key']} --force"
                    )
                elif self.config["key_import_mode"] == "json":
                    self.query_step(json_filepath_query)
                    json_tmp_path = shutil.copy(self.config["json_filepath"], "/tmp/")
                    proc_call(
                        f"sudo -u tezos {suppress_warning_text} tezos-client {tezos_client_options} "
                        f"activate account {baker_alias} with {json_tmp_path} --force"
                    )
                    try:
                        os.remove(json_tmp_path)
                    except:
                        pass
                else:
                    print(f"Please open the Tezos {ledger_app} app on your ledger or")
                    print("press Ctrl+C to go back to the key import mode selection.")
                    ledgers_derivations = wait_for_ledger_app(ledger_app)
                    if ledgers_derivations is None:
                        print("Going back to the import mode selection.")
                        continue
                    ledgers = list(ledgers_derivations.keys())
                    baker_ledger_url = ""
                    while re.match(ledger_regex.decode(), baker_ledger_url) is None:
                        self.query_step(
                            get_ledger_derivation_query(
                                ledgers_derivations,
                                self.config["node_rpc_addr"],
                            )
                        )
                        if self.config["ledger_derivation"] == "Go back":
                            self.import_key(key_mode_query, ledger_app)
                            return
                        elif (
                            self.config["ledger_derivation"]
                            == "Specify derivation path"
                        ):
                            if len(ledgers) >= 1:
                                # If there is only one connected ledger, there is nothing to choose from
                                if len(ledgers) == 1:
                                    ledger_url = ledgers[0]
                                else:
                                    self.query_step(get_ledger_url_query(ledgers))
                                    ledger_url = self.config["ledger_url"]
                                self.query_step(derivation_path_query)
                                signing_curves = [
                                    "bip25519",
                                    "ed25519",
                                    "secp256k1",
                                    "P-256",
                                ]
                                for signing_curve in signing_curves:
                                    ledgers_derivations.setdefault(
                                        ledger_url, []
                                    ).append(
                                        signing_curve
                                        + "/"
                                        + self.config["derivation_path"]
                                    )
                        else:
                            baker_ledger_url = self.config["ledger_derivation"]
                    proc_call(
                        f"sudo -u tezos {suppress_warning_text} tezos-client {tezos_client_options} "
                        f"import secret key {baker_alias} {baker_ledger_url} --force"
                    )

            except EOFError:
                raise EOFError
            except Exception as e:
                print("Something went wrong when calling tezos-client:")
                print(str(e))
                print()
                print("Please check your input and try again.")
            else:
                valid_choice = True
                value, _ = get_key_address(
                    tezos_client_options, self.config["baker_alias"]
                )
                self.config["baker_key_value"] = value
