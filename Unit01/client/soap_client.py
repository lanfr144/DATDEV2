"""
Book&Ride - Unit 01 - SOAP client (DATOP2 Unit 01, "2.2 SOAP").

SOAP is a PROTOCOL, not a style: the message is always an XML Envelope with
an optional Header and a mandatory Body, described by a WSDL contract. No
library is needed to see it: we POST the envelope by hand with requests.

Public test service (free, no key): NumberConversion
    WSDL: https://www.dataaccess.com/webservicesserver/NumberConversion.wso?WSDL
    NumberToWords(42) -> "forty two"

Compare with the REST client: ONE URL for every operation, the operation name
is in the XML body (and the SOAPAction header), the answer is XML too, and
errors come back as a <soap:Fault> element instead of only an HTTP code.

Usage:  python client/soap_client.py [number]
"""
import sys
import xml.etree.ElementTree as ET

import requests

URL = "https://www.dataaccess.com/webservicesserver/NumberConversion.wso"
NS = {"soap": "http://schemas.xmlsoap.org/soap/envelope/",
      "m": "http://www.dataaccess.com/webservicesserver/"}

ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Header/>                                   <!-- metadata: auth, WS-Security... -->
  <soap:Body>
    <NumberToWords xmlns="http://www.dataaccess.com/webservicesserver/">
      <ubiNum>{number}</ubiNum>                    <!-- typed by the WSDL: unsigned long -->
    </NumberToWords>
  </soap:Body>
</soap:Envelope>"""


def number_to_words(number: str) -> str:
    body = ENVELOPE.format(number=number)
    r = requests.post(URL, data=body.encode(), timeout=10,
                      headers={"Content-Type": "text/xml; charset=utf-8"})
    print(f"POST {URL} -> {r.status_code} ({len(body)} bytes of XML sent)")
    root = ET.fromstring(r.content)
    fault = root.find(".//soap:Fault", NS)
    if fault is not None:                            # standardised error handling of SOAP
        raise RuntimeError(f"SOAP Fault: {fault.findtext('faultstring')}")
    return root.findtext(".//m:NumberToWordsResult", namespaces=NS).strip()


if __name__ == "__main__":
    n = sys.argv[1] if len(sys.argv) > 1 else "42"
    try:
        print(f"NumberToWords({n}) = {number_to_words(n)!r}")
    except requests.RequestException as exc:
        print(f"service unreachable (network or proxy): {exc}")
        sys.exit(1)
