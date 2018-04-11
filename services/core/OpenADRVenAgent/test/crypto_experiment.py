# -*- coding: utf-8 -*- {{{
# vim: set fenc=utf-8 ft=python sw=4 ts=4 sts=4 et:
#
# Copyright 2017, Battelle Memorial Institute.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This material was prepared as an account of work sponsored by an agency of
# the United States Government. Neither the United States Government nor the
# United States Department of Energy, nor Battelle, nor any of their
# employees, nor any jurisdiction or organization that has cooperated in the
# development of these materials, makes any warranty, express or
# implied, or assumes any legal liability or responsibility for the accuracy,
# completeness, or usefulness or any information, apparatus, product,
# software, or process disclosed, or represents that its use would not infringe
# privately owned rights. Reference herein to any specific commercial product,
# process, or service by trade name, trademark, manufacturer, or otherwise
# does not necessarily constitute or imply its endorsement, recommendation, or
# favoring by the United States Government or any agency thereof, or
# Battelle Memorial Institute. The views and opinions of authors expressed
# herein do not necessarily state or reflect those of the
# United States Government or any agency thereof.
#
# PACIFIC NORTHWEST NATIONAL LABORATORY operated by
# BATTELLE for the UNITED STATES DEPARTMENT OF ENERGY
# under Contract DE-AC05-76RL01830
# }}}

import signxml
import lxml.etree as etree_
import StringIO
import openadrven.oadr_20b

# Run this experiment from $VOLTTRON_ROOT/services/core/OpenADRVenAgent: "python crypto_experiment.py"

# X509 certificates generated by Kyrio
CERTS_DIRECTORY = 'certs/'
CERT_FILENAME = 'TEST_RSA_VEN_171024145702_cert.pem'            # The VEN certificate issued by the CA.
KEY_FILENAME = 'TEST_RSA_VEN_171024145702_privkey.pem'          # The VEN's private key.
VTN_CA_CERT_FILENAME = 'TEST_OpenADR_RSA_BOTH0002_Cert.pem'     # The concatenated root and intermediate certificates.

XML_PREFIX = '<?xml version="1.0" encoding="UTF-8"?>\n'
PAYLOAD_START_TAG = '<oadr:oadrPayload ' + \
                    'xmlns:oadr="http://openadr.org/oadr-2.0b/2012/07" ' + \
                    'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" >'
PAYLOAD_END_TAG = '</oadr:oadrPayload>'

def pretty_print_lxml(label, lxml_string):
    if label:
        print(label)
    print(etree_.tostring(lxml_string, pretty_print=True))


HAND_BUILT_PAYLOAD = False

signed_object_xml = open('test/xml/crypto_experiment.xml', 'rb').read()
signed_object_lxml = etree_.fromstring(signed_object_xml)

pretty_print_lxml('Original XML to be signed:', signed_object_lxml)
# Use "detached method": the signature lives alonside the signed object in the XML element tree.
# Use c14n "exclusive canonicalization": the signature is independent of namespace inclusion/exclusion.
signer = signxml.XMLSigner(method=signxml.methods.detached,
                           c14n_algorithm='http://www.w3.org/2001/10/xml-exc-c14n#')
signature_lxml = signer.sign(signed_object_lxml,
                             key=open(CERTS_DIRECTORY + KEY_FILENAME, 'rb').read(),
                             cert=open(CERTS_DIRECTORY + CERT_FILENAME, 'rb').read())
pretty_print_lxml('Signed root:', signature_lxml)
signature_xml = etree_.tostring(signature_lxml)

if HAND_BUILT_PAYLOAD:
    payload = XML_PREFIX + PAYLOAD_START_TAG + signature_xml + signed_object_xml + PAYLOAD_END_TAG
else:
    payload = etree_.Element("{http://openadr.org/oadr-2.0b/2012/07}oadrPayload",
                             nsmap=signed_object_lxml.nsmap)
    payload.append(signature_lxml)
    payload.append(signed_object_lxml)
    pretty_print_lxml('Payload:', payload)

# Confirm that the signed payload can be verified.
verif = signxml.XMLVerifier().verify(payload, ca_pem_file=CERTS_DIRECTORY + VTN_CA_CERT_FILENAME)
verified_data_lxml = verif.signed_xml
pretty_print_lxml('Verified data:', verified_data_lxml)