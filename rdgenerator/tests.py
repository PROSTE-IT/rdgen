import errno
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .api_views import validate_generate_params
from .forms import GenerateForm
from .models import GithubRun
from .views import (
    _get_run_status,
    allocate_pit_version,
    managed_update_channel,
    remove_new_version_notification,
    use_self_hosted_runner,
)


class ReverseProxySettingsTests(SimpleTestCase):
    @staticmethod
    def load_settings(**environment):
        process_environment = os.environ.copy()
        for name in (
            'CSRF_TRUSTED_ORIGINS',
            'TRUST_X_FORWARDED_PROTO',
            'CSRF_COOKIE_SECURE',
            'SESSION_COOKIE_SECURE',
        ):
            process_environment.pop(name, None)
        process_environment.update(environment)

        script = (
            'import json; from rdgen import settings; '
            'print(json.dumps({'
            '"origins": settings.CSRF_TRUSTED_ORIGINS, '
            '"proxy": getattr(settings, "SECURE_PROXY_SSL_HEADER", None), '
            '"csrf_secure": settings.CSRF_COOKIE_SECURE, '
            '"session_secure": settings.SESSION_COOKIE_SECURE'
            '}))'
        )
        result = subprocess.run(
            [sys.executable, '-c', script],
            cwd=Path(__file__).resolve().parent.parent,
            env=process_environment,
            capture_output=True,
            check=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_https_genurl_configures_reverse_proxy_defaults(self):
        configured = self.load_settings(
            GENURL='https://rdgen.prosteit.pl/',
            PROTOCOL='https',
        )

        self.assertEqual(
            configured['origins'],
            ['https://rdgen.prosteit.pl'],
        )
        self.assertEqual(
            configured['proxy'],
            ['HTTP_X_FORWARDED_PROTO', 'https'],
        )
        self.assertTrue(configured['csrf_secure'])
        self.assertTrue(configured['session_secure'])

    def test_empty_public_url_keeps_local_http_cookie_defaults(self):
        configured = self.load_settings(
            GENURL='',
            PROTOCOL='https',
        )

        self.assertEqual(configured['origins'], [])
        self.assertIsNone(configured['proxy'])
        self.assertFalse(configured['csrf_secure'])
        self.assertFalse(configured['session_secure'])

    def test_explicit_origins_and_proxy_opt_out_are_supported(self):
        configured = self.load_settings(
            GENURL='https://ignored.example',
            PROTOCOL='https',
            CSRF_TRUSTED_ORIGINS=(
                'https://one.example, https://two.example/'
            ),
            TRUST_X_FORWARDED_PROTO='false',
            CSRF_COOKIE_SECURE='false',
            SESSION_COOKIE_SECURE='false',
        )

        self.assertEqual(
            configured['origins'],
            ['https://one.example', 'https://two.example'],
        )
        self.assertIsNone(configured['proxy'])
        self.assertFalse(configured['csrf_secure'])
        self.assertFalse(configured['session_secure'])


class SupportAddressBookValidationTests(SimpleTestCase):
    def form_data(self, **overrides):
        data = {
            'platform': 'windows',
            'version': '1.4.9',
            'exename': 'support',
            'direction': 'both',
            'installation': 'installationY',
            'settings': 'settingsY',
            'theme': 'system',
            'themeDorO': 'default',
            'passApproveMode': 'password-click',
            'permissionsDorO': 'default',
            'permissionsType': 'custom',
            'supportAddressBook': True,
            'supportAddressBookUrl': 'https://rdbk.prosteit.pl',
        }
        data.update(overrides)
        return data

    def test_form_accepts_supported_build(self):
        form = GenerateForm(data=self.form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_rejects_unsupported_version(self):
        form = GenerateForm(data=self.form_data(version='1.4.8'))
        self.assertFalse(form.is_valid())
        self.assertIn('version', form.errors)

    def test_api_accepts_supported_build(self):
        cleaned, errors = validate_generate_params(self.form_data())
        self.assertFalse(errors)
        self.assertTrue(cleaned['supportAddressBook'])

    def test_api_rejects_unsupported_platform(self):
        _, errors = validate_generate_params(self.form_data(platform='linux'))
        self.assertIn('platform', errors)

    def test_helpdesk_form_requires_unattended_access_password(self):
        form = GenerateForm(data=self.form_data(
            direction='incoming',
            permanentPassword='',
        ))

        self.assertFalse(form.is_valid())
        self.assertIn('permanentPassword', form.errors)

    def test_helpdesk_api_requires_unattended_access_password(self):
        _, errors = validate_generate_params(self.form_data(
            direction='incoming',
            permanentPassword='',
        ))

        self.assertIn('permanentPassword', errors)

    def test_helpdesk_accepts_password_or_password_and_click_modes(self):
        for mode in ('password', 'password-click'):
            with self.subTest(mode=mode):
                form = GenerateForm(data=self.form_data(
                    direction='incoming',
                    permanentPassword='unattended-test-password',
                    passApproveMode=mode,
                ))
                self.assertTrue(form.is_valid(), form.errors)

    def test_helpdesk_rejects_click_only_approval(self):
        form = GenerateForm(data=self.form_data(
            direction='incoming',
            permanentPassword='unattended-test-password',
            passApproveMode='click',
        ))

        self.assertFalse(form.is_valid())
        self.assertIn('passApproveMode', form.errors)

    def test_support_build_always_removes_upstream_update_notification(self):
        self.assertTrue(remove_new_version_notification({
            'supportAddressBook': True,
            'removeNewVersionNotif': False,
        }))

    def test_regular_build_keeps_explicit_update_notification_setting(self):
        self.assertFalse(remove_new_version_notification({
            'supportAddressBook': False,
            'removeNewVersionNotif': False,
        }))
        self.assertTrue(remove_new_version_notification({
            'supportAddressBook': False,
            'removeNewVersionNotif': True,
        }))

    def test_quick_support_form_enforces_installable_incoming_profile(self):
        form = GenerateForm(data=self.form_data(
            buildProfile='quick_support',
            direction='both',
            installation='installationY',
            settings='settingsY',
            permanentPassword='must-not-be-embedded',
            hidecm=True,
        ))

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['direction'], 'incoming')
        self.assertEqual(form.cleaned_data['installation'], 'installationY')
        self.assertEqual(form.cleaned_data['settings'], 'settingsN')
        self.assertFalse(form.cleaned_data['supportAddressBook'])
        self.assertEqual(form.cleaned_data['permanentPassword'], '')
        self.assertFalse(form.cleaned_data['hidecm'])
        self.assertTrue(form.cleaned_data['removeNewVersionNotif'])

    def test_quick_support_api_enforces_installable_incoming_profile(self):
        cleaned, errors = validate_generate_params(self.form_data(
            buildProfile='quick_support',
            supportAddressBook=True,
            supportAddressBookUrl='',
            direction='outgoing',
            installation='installationY',
            settings='settingsY',
            permanentPassword='must-not-be-embedded',
            hidecm=True,
        ))

        self.assertFalse(errors)
        self.assertEqual(cleaned['direction'], 'incoming')
        self.assertEqual(cleaned['installation'], 'installationY')
        self.assertEqual(cleaned['settings'], 'settingsN')
        self.assertFalse(cleaned['supportAddressBook'])
        self.assertEqual(cleaned['permanentPassword'], '')
        self.assertFalse(cleaned['hidecm'])

    def test_quick_support_rejects_non_windows_platform(self):
        form = GenerateForm(data=self.form_data(
            buildProfile='quick_support',
            platform='linux',
        ))

        self.assertFalse(form.is_valid())
        self.assertIn('platform', form.errors)

    def test_update_channel_follows_connection_capability(self):
        self.assertEqual(
            managed_update_channel(
                enabled=True,
                platform='windows',
                direction='incoming',
            ),
            'windows_helpdesk',
        )
        for direction in ('outgoing', 'both'):
            with self.subTest(direction=direction):
                self.assertEqual(
                    managed_update_channel(
                        enabled=True,
                        platform='windows',
                        direction=direction,
                    ),
                    'windows_support',
                )

    def test_regular_build_has_no_managed_update_channel(self):
        self.assertEqual(
            managed_update_channel(
                enabled=False,
                platform='windows',
                direction='both',
            ),
            '',
        )

    def test_quick_support_installs_into_helpdesk_update_channel(self):
        self.assertEqual(
            managed_update_channel(
                enabled=True,
                platform='windows',
                direction='incoming',
                build_profile='quick_support',
            ),
            'windows_helpdesk',
        )


class GeneratorConfigurationPageTests(SimpleTestCase):
    def test_legacy_configuration_requires_explicit_profile_choice(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="legacyConfigReview"')
        self.assertContains(response, 'data-legacy-profile="windows_support"')
        self.assertContains(response, 'data-legacy-profile="windows_helpdesk"')
        self.assertContains(response, 'data-legacy-profile="standard"')
        self.assertContains(response, 'data-legacy-profile="quick_support"')
        self.assertContains(response, 'RDGEN_CONFIG_SCHEMA_VERSION = 2')


class SelfHostedRunnerSelectionTests(SimpleTestCase):
    @override_settings(SH_SECRET='')
    def test_empty_configured_and_submitted_secrets_use_github_runner(self):
        self.assertFalse(use_self_hosted_runner(''))

    @override_settings(SH_SECRET='runner-secret')
    def test_non_empty_matching_secret_uses_self_hosted_runner(self):
        self.assertTrue(use_self_hosted_runner('runner-secret'))

    @override_settings(SH_SECRET='runner-secret')
    def test_missing_or_wrong_secret_uses_github_runner(self):
        self.assertFalse(use_self_hosted_runner(''))
        self.assertFalse(use_self_hosted_runner('wrong-secret'))


class BuildVersionSequenceTests(TestCase):
    def test_revisions_are_shared_by_all_build_variants(self):
        first_version, first_revision = allocate_pit_version('1.4.9')
        second_version, second_revision = allocate_pit_version('1.4.9')

        self.assertEqual((first_version, first_revision), ('1.4.9-pit.1', 1))
        self.assertEqual((second_version, second_revision), ('1.4.9-pit.2', 2))

    def test_new_upstream_version_starts_its_own_sequence(self):
        allocate_pit_version('1.4.9')

        version, revision = allocate_pit_version('1.5.0')

        self.assertEqual((version, revision), ('1.5.0-pit.1', 1))

    def test_master_does_not_allocate_a_product_version(self):
        self.assertEqual(allocate_pit_version('master'), ('', None))


@override_settings(
    RDGEN_DASHBOARD_TOKEN='dashboard-test-token',
    RDGEN_UPLOAD_TOKEN='upload-test-token',
)
class BuildArtifactAPITests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.trash_dir = Path(self.temp_dir.name) / 'trash'
        self.override = override_settings(
            EXE_ROOT=Path(self.temp_dir.name),
            EXE_TRASH_ROOT=self.trash_dir,
        )
        self.override.enable()
        self.build_uuid = str(uuid.uuid4())
        self.build_dir = Path(self.temp_dir.name) / self.build_uuid
        self.build_dir.mkdir()
        (self.build_dir / 'proste_IT_Support.exe').write_bytes(b'EXE')
        (self.build_dir / 'proste_IT_Support.msi').write_bytes(b'MSI')

    def tearDown(self):
        self.override.disable()
        self.temp_dir.cleanup()

    def auth(self):
        return {'HTTP_AUTHORIZATION': 'Bearer dashboard-test-token'}

    def test_build_list_requires_service_token(self):
        response = self.client.get('/api/builds')
        self.assertEqual(response.status_code, 403)

    def test_build_list_discovers_existing_artifacts_without_database_record(self):
        response = self.client.get('/api/builds', **self.auth())
        self.assertEqual(response.status_code, 200)
        build = response.json()['builds'][0]
        self.assertEqual(build['uuid'], self.build_uuid)
        self.assertEqual(build['status'], 'success')
        self.assertEqual(
            {artifact['name'] for artifact in build['artifacts']},
            {'proste_IT_Support.exe', 'proste_IT_Support.msi'},
        )

    def test_successful_run_without_artifacts_is_marked_missing(self):
        missing_uuid = str(uuid.uuid4())
        GithubRun.objects.create(
            id=123,
            uuid=missing_uuid,
            status='success',
            github_run_id=456,
            base_version='1.4.9',
            pit_revision=7,
            pit_version='1.4.9-pit.7',
            connection_direction='both',
            update_channel='windows_support',
        )

        response = self.client.get('/api/builds', **self.auth())

        self.assertEqual(response.status_code, 200)
        build = next(
            item for item in response.json()['builds']
            if item['uuid'] == missing_uuid
        )
        self.assertEqual(build['status'], 'artifact_missing')
        self.assertEqual(build['github_run_id'], 456)
        self.assertEqual(build['pit_version'], '1.4.9-pit.7')
        self.assertEqual(build['connection_direction'], 'both')
        self.assertEqual(build['update_channel'], 'windows_support')
        self.assertEqual(build['artifacts'], [])

    @patch('rdgenerator.views.requests.get')
    def test_active_run_exposes_approximate_step_progress(self, request_get):
        active_uuid = str(uuid.uuid4())
        GithubRun.objects.create(
            id=124,
            uuid=active_uuid,
            status='in_progress',
            github_run_id=789,
        )
        run_response = Mock(status_code=200)
        run_response.json.return_value = {
            'status': 'in_progress',
            'conclusion': None,
        }
        jobs_response = Mock(status_code=200)
        jobs_response.json.return_value = {
            'jobs': [
                {
                    'name': 'build',
                    'status': 'in_progress',
                    'steps': [
                        {'name': 'Checkout', 'status': 'completed'},
                        {'name': 'Compile RustDesk', 'status': 'in_progress'},
                        {'name': 'Package', 'status': 'queued'},
                    ],
                }
            ]
        }
        request_get.side_effect = [run_response, jobs_response]

        result = _get_run_status(active_uuid)

        self.assertEqual(result['current_stage'], 'Compile RustDesk')
        self.assertEqual(result['completed_steps'], 1)
        self.assertEqual(result['total_steps'], 3)
        self.assertGreater(result['progress_percent'], 5)
        self.assertLess(result['progress_percent'], 95)

    def test_artifact_download_is_streamed_and_requires_token(self):
        url = (
            f'/api/builds/{self.build_uuid}/artifacts/'
            'proste_IT_Support.exe'
        )
        self.assertEqual(self.client.get(url).status_code, 403)

        response = self.client.get(url, **self.auth())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'EXE')

    def test_artifact_delete_moves_file_to_recoverable_trash(self):
        url = (
            f'/api/builds/{self.build_uuid}/artifacts/'
            'proste_IT_Support.exe'
        )
        self.assertEqual(self.client.delete(url).status_code, 403)

        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.delete(url, **self.auth())

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['recoverable'])
        self.assertFalse((self.build_dir / 'proste_IT_Support.exe').exists())
        trashed = list((self.trash_dir / self.build_uuid).iterdir())
        self.assertEqual(len(trashed), 1)
        self.assertTrue(trashed[0].name.endswith('-proste_IT_Support.exe'))

    @patch(
        'rdgenerator.views.os.replace',
        side_effect=OSError(errno.EXDEV, 'Invalid cross-device link'),
    )
    def test_artifact_delete_falls_back_across_mounts(self, replace):
        url = (
            f'/api/builds/{self.build_uuid}/artifacts/'
            'proste_IT_Support.exe'
        )

        response = self.client.delete(url, **self.auth())

        self.assertEqual(response.status_code, 200)
        replace.assert_called_once()
        self.assertFalse((self.build_dir / 'proste_IT_Support.exe').exists())
        trashed = list((self.trash_dir / self.build_uuid).iterdir())
        self.assertEqual(len(trashed), 1)
        self.assertTrue(trashed[0].is_file())

    def test_build_delete_hides_run_and_moves_all_artifacts_to_trash(self):
        GithubRun.objects.create(
            id=125,
            uuid=self.build_uuid,
            status='success',
            github_run_id=790,
        )
        url = f'/api/builds/{self.build_uuid}'

        self.assertEqual(self.client.delete(url).status_code, 403)
        response = self.client.delete(url, **self.auth())

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['deleted'])
        self.assertTrue(response.json()['recoverable'])
        self.assertFalse(self.build_dir.exists())
        trashed_builds = list((self.trash_dir / self.build_uuid).iterdir())
        self.assertEqual(len(trashed_builds), 1)
        self.assertTrue(trashed_builds[0].is_dir())
        self.assertEqual(
            {item.name for item in trashed_builds[0].iterdir()},
            {'proste_IT_Support.exe', 'proste_IT_Support.msi'},
        )
        run = GithubRun.objects.get(uuid=self.build_uuid)
        self.assertIsNotNone(run.deleted_at)
        listed = self.client.get('/api/builds', **self.auth()).json()['builds']
        self.assertNotIn(self.build_uuid, {item['uuid'] for item in listed})
        status = self.client.get(
            f'/api/status?uuid={self.build_uuid}',
            **self.auth(),
        )
        self.assertEqual(status.status_code, 404)

    @patch(
        'rdgenerator.views.os.replace',
        side_effect=OSError(errno.EXDEV, 'Invalid cross-device link'),
    )
    def test_build_delete_falls_back_across_mounts(self, replace):
        GithubRun.objects.create(
            id=127,
            uuid=self.build_uuid,
            status='failure',
            github_run_id=792,
        )

        response = self.client.delete(
            f'/api/builds/{self.build_uuid}',
            **self.auth(),
        )

        self.assertEqual(response.status_code, 200)
        replace.assert_called_once()
        self.assertFalse(self.build_dir.exists())
        trashed = list((self.trash_dir / self.build_uuid).iterdir())
        self.assertEqual(len(trashed), 1)
        self.assertTrue(trashed[0].is_dir())
        self.assertIsNotNone(
            GithubRun.objects.get(uuid=self.build_uuid).deleted_at
        )

    def test_active_build_cannot_be_deleted(self):
        GithubRun.objects.create(
            id=126,
            uuid=self.build_uuid,
            status='in_progress',
            github_run_id=791,
        )

        response = self.client.delete(
            f'/api/builds/{self.build_uuid}',
            **self.auth(),
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(self.build_dir.exists())
        self.assertIsNone(GithubRun.objects.get(uuid=self.build_uuid).deleted_at)

    def test_legacy_download_rejects_path_traversal(self):
        response = self.client.get(
            '/download',
            {
                'uuid': self.build_uuid,
                'filename': '../db.sqlite3',
            },
            **self.auth(),
        )
        self.assertEqual(response.status_code, 404)

    def test_artifact_upload_requires_the_separate_upload_token(self):
        payload = {
            'uuid': self.build_uuid,
            'file': SimpleUploadedFile('new-build.exe', b'new'),
        }
        self.assertEqual(
            self.client.post('/save_custom_client', payload).status_code,
            403,
        )

        payload['file'] = SimpleUploadedFile('new-build.exe', b'new')
        response = self.client.post(
            '/save_custom_client',
            payload,
            HTTP_AUTHORIZATION='Bearer upload-test-token',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual((self.build_dir / 'new-build.exe').read_bytes(), b'new')

    def test_artifact_upload_accepts_complete_batch(self):
        response = self.client.post(
            '/save_custom_client',
            {
                'uuid': self.build_uuid,
                'file': [
                    SimpleUploadedFile('batch-build.exe', b'EXE batch'),
                    SimpleUploadedFile('batch-build.msi', b'MSI batch'),
                ],
            },
            HTTP_AUTHORIZATION='Bearer upload-test-token',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            (self.build_dir / 'batch-build.exe').read_bytes(),
            b'EXE batch',
        )
        self.assertEqual(
            (self.build_dir / 'batch-build.msi').read_bytes(),
            b'MSI batch',
        )

    def test_artifact_upload_validates_entire_batch_before_writing(self):
        response = self.client.post(
            '/save_custom_client',
            {
                'uuid': self.build_uuid,
                'file': [
                    SimpleUploadedFile('not-written.exe', b'EXE'),
                    SimpleUploadedFile('invalid.txt', b'not an artifact'),
                ],
            },
            HTTP_AUTHORIZATION='Bearer upload-test-token',
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse((self.build_dir / 'not-written.exe').exists())

    def test_artifact_upload_rejects_empty_request(self):
        response = self.client.post(
            '/save_custom_client',
            {'uuid': self.build_uuid},
            HTTP_AUTHORIZATION='Bearer upload-test-token',
        )

        self.assertEqual(response.status_code, 400)
