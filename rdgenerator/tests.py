from django.test import SimpleTestCase

from .api_views import validate_generate_params
from .forms import GenerateForm


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
