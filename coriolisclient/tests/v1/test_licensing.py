# Copyright 2024 Cloudbase Solutions Srl
# All Rights Reserved.

from unittest import mock

import requests

from coriolisclient import constants
from coriolisclient import exceptions
from coriolisclient.tests import test_base
from coriolisclient.v1 import licensing

_STANDARD_STATS = {
    'current_performed_migrations': 1,
    'current_performed_replicas': 2,
    'current_available_migrations': 3,
    'current_available_replicas': 4,
    'lifetime_performed_migrations': 5,
    'lifetime_performed_replicas': 6,
    'lifetime_available_migrations': 7,
    'lifetime_available_replicas': 8,
}

_SAP_STATS = {
    'current_performed_migrations': 10,
    'current_performed_replicas': 20,
    'current_available_migrations': 30,
    'current_available_replicas': 40,
    'lifetime_performed_migrations': 50,
    'lifetime_performed_replicas': 60,
    'lifetime_available_migrations': 70,
    'lifetime_available_replicas': 80,
}

_EMPTY_STATS = dict.fromkeys(constants.LICENCE_STATS_FIELDS, 0)


class LicensingClientTestCase(
    test_base.CoriolisBaseTestCase):
    """Test suite for the Coriolis v1 Licensing Client."""

    def setUp(self):
        mock_client = mock.Mock()
        super(LicensingClientTestCase, self).setUp()
        self.licence = licensing.LicensingClient(
            mock_client, "endpoint_name")
        mock_client.verify = True
        self.licence._cli = mock_client

    def test_get_licensing_endpoint_url(self):
        self.licence._cli.get_endpoint.return_value = "url/endpoint_url/"

        result = self.licence._get_licensing_endpoint_url()

        self.assertEqual(
            "url/endpoint_url",
            result
        )
        self.licence._cli.get_endpoint.assert_called_once_with(
            service_type="endpoint_name")

    def test_get_licensing_endpoint_url_raises(self):
        self.licence._cli.get_endpoint.side_effect = Exception()

        with self.assertLogs(level="WARN"):
            self.assertRaises(
                exceptions.LicensingEndpointNotFound,
                self.licence._get_licensing_endpoint_url
            )
            self.licence._cli.get_endpoint.assert_called_once_with(
                service_type="endpoint_name")

    @mock.patch.object(licensing.LicensingClient,
                       "_get_licensing_endpoint_url")
    def test_do_req_raw(
        self,
        mock_get_licensing_endpoint_url
    ):
        mock_method = mock.Mock()
        mock_resp = mock.Mock()
        mock_resp.ok = True
        mock_method.return_value = mock_resp
        setattr(requests, "mock_method", mock_method)
        mock_get_licensing_endpoint_url.return_value = 'url/endpoint_url/'
        result = self.licence._do_req(
            method_name="mock_method",
            resource='url/resource_url/',
            body=None,
            response_key=None,
            raw_response=True
        )

        self.assertEqual(
            mock_resp,
            result
        )
        mock_method.assert_called_once_with(
            'url/endpoint_url/url/resource_url/',
            verify=self.licence._cli.verify
        )

    @mock.patch.object(licensing.LicensingClient,
                       "_get_licensing_endpoint_url")
    def test_do_req_json(
        self,
        mock_get_licensing_endpoint_url
    ):
        mock_method = mock.Mock()
        mock_resp = mock.Mock()
        mock_resp.ok = True
        mock_resp.json.return_value = {"response_key": mock.sentinel.data}
        mock_method.return_value = mock_resp
        setattr(requests, "mock_method", mock_method)
        mock_get_licensing_endpoint_url.return_value = 'url/endpoint_url/'
        result = self.licence._do_req(
            method_name="mock_method",
            resource='url/resource_url/',
            body={"mock_body": "value"},
            response_key='response_key',
            raw_response=False
        )

        self.assertEqual(
            mock.sentinel.data,
            result
        )
        mock_method.assert_called_once_with(
            'url/endpoint_url/url/resource_url/',
            verify=self.licence._cli.verify,
            data='{"mock_body": "value"}'
        )

    @mock.patch.object(licensing.LicensingClient,
                       "_get_licensing_endpoint_url")
    def test_do_req_error(
        self,
        mock_get_licensing_endpoint_url
    ):
        mock_method = mock.Mock()
        mock_resp = mock.Mock()
        mock_resp.ok = False
        mock_resp.json.side_effect = Exception
        mock_resp.raise_for_status.side_effect = exceptions.CoriolisException
        mock_method.return_value = mock_resp
        setattr(requests, "mock_method", mock_method)
        mock_get_licensing_endpoint_url.return_value = 'url/endpoint_url/'

        with self.assertLogs(level="DEBUG"):
            self.assertRaises(
                exceptions.CoriolisException,
                self.licence._do_req,
                method_name="mock_method",
                resource='url/resource_url/',
                body=None,
                response_key='response_key',
                raw_response=False
            )
            mock_method.assert_called_once_with(
                'url/endpoint_url/url/resource_url/',
                verify=self.licence._cli.verify
            )

    @mock.patch.object(licensing.LicensingClient,
                       "_get_licensing_endpoint_url")
    def test_do_req_http_error(
        self,
        mock_get_licensing_endpoint_url
    ):
        mock_method = mock.Mock()
        mock_resp = mock.Mock()
        mock_resp.ok = False
        mock_resp.json.return_value = {"error": {"code": 123, "message": ""}}
        mock_method.return_value = mock_resp
        setattr(requests, "mock_method", mock_method)
        mock_get_licensing_endpoint_url.return_value = 'url/endpoint_url/'

        self.assertRaises(
            exceptions.HTTPError,
            self.licence._do_req,
            method_name="mock_method",
            resource='url/resource_url/',
            body=None,
            response_key='response_key',
            raw_response=False
        )
        mock_method.assert_called_once_with(
            'url/endpoint_url/url/resource_url/',
            verify=self.licence._cli.verify
        )

    @mock.patch.object(licensing.LicensingClient,
                       "_get_licensing_endpoint_url")
    def test_do_req_response_key_error(
        self,
        mock_get_licensing_endpoint_url
    ):
        mock_method = mock.Mock()
        mock_resp = mock.Mock()
        mock_resp.ok = False
        mock_resp.json.return_value = {"response_key": mock.sentinel.data}
        mock_method.return_value = mock_resp
        setattr(requests, "mock_method", mock_method)
        mock_get_licensing_endpoint_url.return_value = 'url/endpoint_url/'

        self.assertRaises(
            ValueError,
            self.licence._do_req,
            method_name="mock_method",
            resource='url/resource_url/',
            body=None,
            response_key='invalid',
            raw_response=False
        )
        mock_method.assert_called_once_with(
            'url/endpoint_url/url/resource_url/',
            verify=self.licence._cli.verify
        )

    def test_do_req_method_error(self):
        setattr(requests, "mock_method", None)

        self.assertRaises(
            ValueError,
            self.licence._do_req,
            method_name="mock_method",
            resource='url/resource_url/',
            body=None,
            response_key='invalid',
            raw_response=False
        )

    @mock.patch.object(licensing.LicensingClient, '_do_req')
    def test_get(self, mock_do_req):
        result = self.licence.get(
            resource=mock.sentinel.resource,
            body=mock.sentinel.body,
            response_key=mock.sentinel.response_key,
            raw_response=False
        )
        self.assertEqual(
            mock_do_req.return_value,
            result
        )
        mock_do_req.assert_called_once_with(
            'GET',
            mock.sentinel.resource,
            response_key=mock.sentinel.response_key,
            body=mock.sentinel.body,
            raw_response=False
        )

    @mock.patch.object(licensing.LicensingClient, '_do_req')
    def test_post(self, mock_do_req):
        result = self.licence.post(
            resource=mock.sentinel.resource,
            body=mock.sentinel.body,
            response_key=mock.sentinel.response_key,
            raw_response=False
        )
        self.assertEqual(
            mock_do_req.return_value,
            result
        )
        mock_do_req.assert_called_once_with(
            'POST',
            mock.sentinel.resource,
            response_key=mock.sentinel.response_key,
            body=mock.sentinel.body,
            raw_response=False
        )

    @mock.patch.object(licensing.LicensingClient, '_do_req')
    def test_delete(self, mock_do_req):
        result = self.licence.delete(
            resource=mock.sentinel.resource,
            body=mock.sentinel.body,
            response_key=mock.sentinel.response_key,
            raw_response=False
        )
        self.assertEqual(
            mock_do_req.return_value,
            result
        )
        mock_do_req.assert_called_once_with(
            'DELETE',
            mock.sentinel.resource,
            response_key=mock.sentinel.response_key,
            body=mock.sentinel.body,
            raw_response=False
        )


class LicensingManagerTestCase(
    test_base.CoriolisBaseTestCase):
    """Test suite for the Coriolis v1 Licensing Client."""

    @mock.patch.object(licensing, 'LicensingClient')
    def setUp(self, mock_LicensingClient):
        mock_client = mock.Mock()
        super(LicensingManagerTestCase, self).setUp()
        self.licence = licensing.LicensingManager(mock_client)
        self.licence._licensing_cli = mock_LicensingClient

    def test_status(self):
        self.licence._licensing_cli.get.return_value = {
            'appliance_id': 'appliance-1',
            'earliest_licence_expiry_time': '2026-04-18T13:13:35Z',
            'latest_licence_expiry_time': '2026-05-19T12:40:21Z',
            constants.LICENCE_STATS_KEY_STANDARD: _STANDARD_STATS,
            constants.LICENCE_STATS_KEY_SAP: _SAP_STATS,
        }

        result = self.licence.status(mock.sentinel.appliance_id)

        self.licence._licensing_cli.get.assert_called_once_with(
            '/appliances/%s/status' % mock.sentinel.appliance_id,
            response_key='appliance_licence_status')
        self.assertIsInstance(result, licensing.ApplianceLicenceStatus)
        self.assertEqual('appliance-1', result.appliance_id)
        self.assertEqual(
            _STANDARD_STATS,
            getattr(result, constants.LICENCE_STATS_KEY_STANDARD))
        self.assertEqual(
            _SAP_STATS, getattr(result, constants.LICENCE_STATS_KEY_SAP))
        # the top-level counters hold the totals across both editions:
        self.assertEqual(
            11, result.current_performed_migrations)
        self.assertEqual(
            ['Standard', 'SAP'], result.licence_editions)

    def test_list(self):
        mock_resource_class = mock.Mock()
        self.licence.resource_class = mock_resource_class
        self.licence._licensing_cli.get.return_value = {
            "licence1": "mock_licence1",
            "licence2": "mock_licence2"
        }

        result = self.licence.list(mock.sentinel.appliance_id)

        self.assertEqual(
            [mock_resource_class.return_value,
             mock_resource_class.return_value],
            result
        )
        self.licence._licensing_cli.get.assert_called_once_with(
            '/appliances/%s/licences' % mock.sentinel.appliance_id,
            response_key='licences')
        mock_resource_class.assert_has_calls([
            mock.call(self.licence, "licence1", loaded=True),
            mock.call(self.licence, "licence2", loaded=True)
        ])

    def test_register(self):
        mock_resource_class = mock.Mock()
        self.licence.resource_class = mock_resource_class

        result = self.licence.register(
            mock.sentinel.appliance_id, mock.sentinel.licence)

        self.assertEqual(
            mock_resource_class.return_value,
            result
        )
        self.licence._licensing_cli.post.assert_called_once_with(
            '/appliances/%s/licences' % mock.sentinel.appliance_id,
            body=mock.sentinel.licence,
            response_key='licence')
        mock_resource_class.assert_called_once_with(
            self.licence, self.licence._licensing_cli.post.return_value,
            loaded=True)

    def test_show(self):
        mock_resource_class = mock.Mock()
        self.licence.resource_class = mock_resource_class

        result = self.licence.show(
            mock.sentinel.appliance_id, mock.sentinel.licence_id)

        self.assertEqual(
            mock_resource_class.return_value,
            result
        )
        self.licence._licensing_cli.get.assert_called_once_with(
            '/appliances/%s/licences/%s' % (mock.sentinel.appliance_id,
                                            mock.sentinel.licence_id),
            response_key='licence')
        mock_resource_class.assert_called_once_with(
            self.licence, self.licence._licensing_cli.get.return_value,
            loaded=True)

    def test_delete(self):
        mock_resource_class = mock.Mock()
        self.licence.resource_class = mock_resource_class

        result = self.licence.delete(
            mock.sentinel.appliance_id, mock.sentinel.licence_id)

        self.assertEqual(
            self.licence._licensing_cli.delete.return_value,
            result
        )
        self.licence._licensing_cli.delete.assert_called_once_with(
            '/appliances/%s/licences/%s' % (mock.sentinel.appliance_id,
                                            mock.sentinel.licence_id),
            raw_response=True)


class LicenceEditionTestCase(test_base.CoriolisBaseTestCase):
    """Test suite for the licence/reservation edition helpers."""

    def test_get_licence_edition(self):
        for version in constants.STANDARD_LICENCE_VERSIONS:
            self.assertEqual(
                constants.LICENCE_EDITION_STANDARD,
                licensing.get_licence_edition(version))
        for version in constants.SAP_LICENCE_VERSIONS:
            self.assertEqual(
                constants.LICENCE_EDITION_SAP,
                licensing.get_licence_edition(version))

    def test_get_licence_edition_unversioned(self):
        # licences which predate licence versioning are standard ones:
        for version in [None, ""]:
            self.assertEqual(
                constants.LICENCE_EDITION_STANDARD,
                licensing.get_licence_edition(version))

    def test_get_licence_edition_unknown(self):
        self.assertEqual(
            "v3-something", licensing.get_licence_edition("v3-something"))

    def test_get_reservation_edition(self):
        for reservation_type in constants.STANDARD_RESERVATION_TYPES:
            self.assertEqual(
                constants.LICENCE_EDITION_STANDARD,
                licensing.get_reservation_edition(reservation_type))
        for reservation_type in constants.SAP_RESERVATION_TYPES:
            self.assertEqual(
                constants.LICENCE_EDITION_SAP,
                licensing.get_reservation_edition(reservation_type))

    def test_get_reservation_edition_unknown(self):
        self.assertIsNone(licensing.get_reservation_edition("something"))
        self.assertIsNone(licensing.get_reservation_edition(None))


class NormalizeApplianceLicenceStatusTestCase(test_base.CoriolisBaseTestCase):
    """Test suite for the appliance licensing status normalization."""

    def test_current_format(self):
        status = {
            'appliance_id': 'appliance-1',
            'earliest_licence_expiry_time': '2026-04-18T13:13:35Z',
            constants.LICENCE_STATS_KEY_STANDARD: dict(_STANDARD_STATS),
            constants.LICENCE_STATS_KEY_SAP: dict(_SAP_STATS),
        }

        result = licensing.normalize_appliance_licence_status(status)

        self.assertEqual('appliance-1', result['appliance_id'])
        self.assertEqual(
            '2026-04-18T13:13:35Z', result['earliest_licence_expiry_time'])
        self.assertEqual(
            _STANDARD_STATS, result[constants.LICENCE_STATS_KEY_STANDARD])
        self.assertEqual(_SAP_STATS, result[constants.LICENCE_STATS_KEY_SAP])
        for field in constants.LICENCE_STATS_FIELDS:
            self.assertEqual(
                _STANDARD_STATS[field] + _SAP_STATS[field], result[field])

    def test_legacy_flat_format(self):
        """A pre-SAP licensing server reports flat counters, all standard."""
        status = {'appliance_id': 'appliance-1'}
        status.update(_STANDARD_STATS)

        result = licensing.normalize_appliance_licence_status(status)

        self.assertEqual(
            _STANDARD_STATS, result[constants.LICENCE_STATS_KEY_STANDARD])
        self.assertEqual(
            _EMPTY_STATS, result[constants.LICENCE_STATS_KEY_SAP])
        for field in constants.LICENCE_STATS_FIELDS:
            self.assertEqual(_STANDARD_STATS[field], result[field])

    def test_missing_stats_bodies_default_to_zeroes(self):
        result = licensing.normalize_appliance_licence_status(
            {'appliance_id': 'appliance-1',
             constants.LICENCE_STATS_KEY_STANDARD: {}})

        self.assertEqual(
            _EMPTY_STATS, result[constants.LICENCE_STATS_KEY_STANDARD])
        self.assertEqual(
            _EMPTY_STATS, result[constants.LICENCE_STATS_KEY_SAP])

    def test_does_not_mutate_the_input(self):
        status = {constants.LICENCE_STATS_KEY_STANDARD: dict(_STANDARD_STATS)}

        licensing.normalize_appliance_licence_status(status)

        self.assertEqual(
            {constants.LICENCE_STATS_KEY_STANDARD: _STANDARD_STATS}, status)

    def test_invalid_status_body(self):
        self.assertRaises(
            ValueError, licensing.normalize_appliance_licence_status, None)

    def test_invalid_stats_body(self):
        self.assertRaises(
            ValueError, licensing.normalize_appliance_licence_status,
            {constants.LICENCE_STATS_KEY_SAP: "not-an-object"})

    def test_invalid_counter_value(self):
        stats = dict(_STANDARD_STATS)
        stats['current_performed_migrations'] = "many"

        self.assertRaises(
            ValueError, licensing.normalize_appliance_licence_status,
            {constants.LICENCE_STATS_KEY_STANDARD: stats})


class ApplianceLicenceStatusTestCase(test_base.CoriolisBaseTestCase):
    """Test suite for the `ApplianceLicenceStatus` resource."""

    def _make_status(self, standard_stats, sap_stats):
        return licensing.ApplianceLicenceStatus(
            mock.Mock(),
            licensing.normalize_appliance_licence_status({
                constants.LICENCE_STATS_KEY_STANDARD: standard_stats,
                constants.LICENCE_STATS_KEY_SAP: sap_stats}),
            loaded=True)

    def test_licence_editions_standard_only(self):
        status = self._make_status(_STANDARD_STATS, dict(_EMPTY_STATS))
        self.assertEqual(['Standard'], status.licence_editions)

    def test_licence_editions_sap_only(self):
        status = self._make_status(dict(_EMPTY_STATS), _SAP_STATS)
        self.assertEqual(['SAP'], status.licence_editions)

    def test_licence_editions_both(self):
        status = self._make_status(_STANDARD_STATS, _SAP_STATS)
        self.assertEqual(['Standard', 'SAP'], status.licence_editions)

    def test_licence_editions_none(self):
        status = self._make_status(dict(_EMPTY_STATS), dict(_EMPTY_STATS))
        self.assertEqual([], status.licence_editions)

    def test_licence_editions_ignores_usage_without_allowance(self):
        """Usage counters alone do not make an edition licenced."""
        stats = dict(_EMPTY_STATS)
        stats['lifetime_performed_replicas'] = 3
        status = self._make_status(_STANDARD_STATS, stats)

        self.assertEqual(['Standard'], status.licence_editions)
