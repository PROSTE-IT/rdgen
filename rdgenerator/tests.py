import tempfile
import uuid
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from .api_views import validate_generate_params
from .forms import GenerateForm
from .views import use_self_hosted_runner


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


@override_settings(
    RDGEN_DASHBOARD_TOKEN='dashboard-test-token',
    RDGEN_UPLOAD_TOKEN='upload-test-token',
)
class BuildArtifactAPITests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.override = override_settings(EXE_ROOT=Path(self.temp_dir.name))
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

    def test_artifact_download_is_streamed_and_requires_token(self):
        url = (
            f'/api/builds/{self.build_uuid}/artifacts/'
            'proste_IT_Support.exe'
        )
        self.assertEqual(self.client.get(url).status_code, 403)

        response = self.client.get(url, **self.auth())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'EXE')

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
