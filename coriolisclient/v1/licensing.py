# Copyright (c) 2020 Cloudbase Solutions Srl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging

import requests

from coriolisclient import base
from coriolisclient import constants
from coriolisclient import exceptions

LOG = logging.getLogger(__name__)
_LICENSING_ENDPOINT_NAME = "coriolis-licensing"


def get_licence_edition(licence_version):
    """Returns the user-facing edition name of a licence version identifier.

    Licences which predate licence versioning carry no version and are
    standard licences, as are all the explicitly versioned 'v1'/'v2' ones.
    Unknown identifiers are returned as-is rather than being misreported as
    standard licences.
    """
    if licence_version in constants.SAP_LICENCE_VERSIONS:
        return constants.LICENCE_EDITION_SAP
    if not licence_version or (
            licence_version in constants.STANDARD_LICENCE_VERSIONS):
        return constants.LICENCE_EDITION_STANDARD
    return licence_version


def get_reservation_edition(reservation_type):
    """Returns the user-facing edition name a reservation counts against.

    Returns `None` for reservation types this client does not know about.
    """
    if reservation_type in constants.SAP_RESERVATION_TYPES:
        return constants.LICENCE_EDITION_SAP
    if reservation_type in constants.STANDARD_RESERVATION_TYPES:
        return constants.LICENCE_EDITION_STANDARD
    return None


def _normalize_licence_stats(stats, stats_key, warn_on_unknown=True):
    """Returns a stats body with every known usage counter defaulted to 0.

    :param stats: the raw stats mapping as returned by the licensing server
    :param stats_key: the name of the stats body, used for error reporting
    :param warn_on_unknown: whether to warn about fields which are not known
        usage counters. Disabled when normalizing a legacy status body, whose
        counters sit alongside unrelated top-level fields.
    """
    if not isinstance(stats, dict):
        raise ValueError(
            "Invalid '%s' in appliance licensing status, expected a JSON "
            "object but got: %r" % (stats_key, stats))

    normalized = {}
    for field in constants.LICENCE_STATS_FIELDS:
        value = stats.get(field)
        if value is None:
            value = 0
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                "Invalid value %r for licensing counter '%s' of '%s' in the "
                "appliance licensing status, expected an integer." % (
                    value, field, stats_key))
        normalized[field] = value

    if warn_on_unknown:
        unknown = set(stats) - set(constants.LICENCE_STATS_FIELDS)
        if unknown:
            LOG.warning(
                "Ignoring unrecognized field(s) %s in the '%s' of the "
                "appliance licensing status. This version of the Coriolis "
                "client may be older than the licensing server.",
                sorted(unknown), stats_key)

    return normalized


def normalize_appliance_licence_status(status):
    """Normalizes an appliance licensing status body.

    The licensing server buckets the usage counters per licence edition
    (under 'standard_licence_stats' and 'sap_licence_stats') ever since the
    SAP licence type was introduced. Licensing servers which predate it
    returned a single flat set of counters covering all licences, which were
    necessarily standard ones, so those get mapped onto the standard bucket.

    Both bodies are additionally given the sum of the two editions' counters
    at the top level, which is exactly what the flat counters used to mean.

    Any other field of the status body is passed through untouched.
    """
    if not isinstance(status, dict):
        raise ValueError(
            "Invalid appliance licensing status, expected a JSON object but "
            "got: %r" % (status,))

    normalized = dict(status)

    standard = status.get(constants.LICENCE_STATS_KEY_STANDARD)
    legacy = standard is None
    if legacy:
        LOG.debug(
            "Appliance licensing status has no '%s', assuming the legacy "
            "flat status format.", constants.LICENCE_STATS_KEY_STANDARD)
        standard = status
    normalized[constants.LICENCE_STATS_KEY_STANDARD] = (
        _normalize_licence_stats(
            standard, constants.LICENCE_STATS_KEY_STANDARD,
            warn_on_unknown=not legacy))

    sap = status.get(constants.LICENCE_STATS_KEY_SAP)
    normalized[constants.LICENCE_STATS_KEY_SAP] = _normalize_licence_stats(
        {} if sap is None else sap, constants.LICENCE_STATS_KEY_SAP)

    for field in constants.LICENCE_STATS_FIELDS:
        normalized[field] = (
            normalized[constants.LICENCE_STATS_KEY_STANDARD][field] +
            normalized[constants.LICENCE_STATS_KEY_SAP][field])

    return normalized


class Licence(base.Resource):
    pass


class ApplianceLicenceStatus(base.Resource):
    """The licensing status of an appliance.

    On top of the fields returned by the licensing server, the usage counters
    of both licence editions are always present (defaulted to zeroes), and
    the top-level counters hold the sum of the two editions.
    """

    @property
    def licence_editions(self):
        """The editions the appliance holds licences for, in display order.

        Empty for an appliance which was never issued any licence at all.
        """
        editions = []
        stats_keys = [
            (constants.LICENCE_STATS_KEY_STANDARD,
             constants.LICENCE_EDITION_STANDARD),
            (constants.LICENCE_STATS_KEY_SAP,
             constants.LICENCE_EDITION_SAP)]
        for stats_key, edition in stats_keys:
            stats = getattr(self, stats_key)
            if any(stats.get(field)
                   for field in constants.LICENCE_STATS_ALLOWANCE_FIELDS):
                editions.append(edition)
        return editions


class LicensingClient(object):

    def __init__(self, client, endpoint_name_override=None):
        self._cli = client
        self._endpoint_name = _LICENSING_ENDPOINT_NAME
        if endpoint_name_override:
            self._endpoint_name = endpoint_name_override

    def _get_licensing_endpoint_url(self):
        endpoint_url = None
        try:
            endpoint_url = self._cli.get_endpoint(
                service_type=self._endpoint_name)
        except Exception as ex:
            LOG.warning("Unable to determine licensing endpoint: %s", str(ex))
            raise exceptions.LicensingEndpointNotFound(self._endpoint_name)
        return endpoint_url.rstrip('/')

    def _do_req(self, method_name, resource, body=None, response_key=None,
                raw_response=False):
        method = getattr(requests, method_name.lower(), None)
        if not method:
            raise ValueError("No such HTTP method '%s'" % method_name)

        endpoint_url = self._get_licensing_endpoint_url()
        url = '%s/%s' % (endpoint_url.rstrip('/'), resource.lstrip('/'))

        kwargs = {"verify": self._cli.verify}
        if body:
            if not isinstance(body, (str, bytes)):
                body = json.dumps(body)
            kwargs["data"] = body

        resp = method(url, **kwargs)

        if not resp.ok:
            # try to extract error from licensing server:
            error = None
            try:
                error = resp.json().get('error', {})
            except (Exception, KeyboardInterrupt) as ex:
                LOG.debug(
                    "Exception occured during error extraction from licensing "
                    "response: '%s'\nException:\n%s",
                    resp.text, ex)
            if error and all([x in error for x in ['code', 'message']]):
                raise exceptions.HTTPError(
                    message=error['message'],
                    status_code=int(error['code']))
            else:
                resp.raise_for_status()

        if raw_response:
            return resp

        else:
            resp_data = resp.json()
            if response_key:
                if response_key not in resp_data:
                    raise ValueError(
                        'No response key "%s" in response body: %s' % (
                            response_key, resp_data))
                resp_data = resp_data[response_key]

        return resp_data

    def get(self, resource, body=None, response_key=None, raw_response=False):
        return self._do_req('GET', resource, response_key=response_key,
                            body=body, raw_response=raw_response)

    def post(self, resource, body=None, response_key=None,
             raw_response=False):
        return self._do_req(
            'POST', resource, body=body, response_key=response_key,
            raw_response=raw_response)

    def delete(self, resource, body=None, response_key=None,
               raw_response=False):
        return self._do_req('DELETE', resource, raw_response=raw_response,
                            body=body, response_key=response_key)


class LicensingManager(base.BaseManager):
    resource_class = Licence

    def __init__(self, api):
        super(LicensingManager, self).__init__(api)
        self._licensing_cli = LicensingClient(api)

    def status(self, appliance_id):
        url = '/appliances/%s/status' % appliance_id
        data = self._licensing_cli.get(
            url, response_key='appliance_licence_status')
        return ApplianceLicenceStatus(
            self, normalize_appliance_licence_status(data), loaded=True)

    def list(self, appliance_id):
        url = '/appliances/%s/licences' % appliance_id
        data = self._licensing_cli.get(url, response_key='licences')
        return [self.resource_class(self, lic, loaded=True)
                for lic in data if lic]

    def register(self, appliance_id, licence):
        url = '/appliances/%s/licences' % appliance_id
        data = self._licensing_cli.post(
            url, body=licence, response_key='licence')
        return self.resource_class(self, data, loaded=True)

    def show(self, appliance_id, licence_id):
        url = '/appliances/%s/licences/%s' % (appliance_id, licence_id)
        data = self._licensing_cli.get(url, response_key='licence')
        return self.resource_class(self, data, loaded=True)

    def delete(self, appliance_id, licence_id):
        url = '/appliances/%s/licences/%s' % (appliance_id, licence_id)
        return self._licensing_cli.delete(url, raw_response=True)
