import base64

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import misc


@tagged('post_install', '-at_install')
class TestPontonEventContractFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.draft_stage = cls.env['event.stage'].create({'name': 'Borrador'})
        cls.confirmed_stage = cls.env['event.stage'].create({
            'name': 'Confirmado',
            'is_contract_confirmed_stage': True,
        })
        cls.review_stage = cls.env['event.stage'].create({'name': 'Revision'})
        cls.organizer = cls.env['res.partner'].create({
            'name': 'Productor Test',
            'email': 'productor@example.com',
            'phone': '1111-2222',
            'vat': '30712345678',
        })
        cls.manso = cls.env['res.partner'].create({
            'name': 'Manso Test',
            'email': 'manso@example.com',
        })
        cls.guido = cls.env['res.partner'].create({
            'name': 'Guido Yamaguchi',
            'email': 'guidoyamaguchi@gmail.com',
        })
        cls.event_analytic = cls.env['account.analytic.account'].create({
            'name': 'Evento contrato test',
            'plan_id': cls.env.ref('ponton_fudo.analytic_plan_eventos').id,
        })
        cls.operation_analytic = cls.env.ref('ponton_fudo.analytic_operation_coproduccion')
        cls.event_type = cls.env['event.type'].create({
            'name': 'Coproduccion',
            'ponton_contract_required': True,
            'ponton_contract_manso_partner_id': cls.manso.id,
            'ponton_contract_validity_days': 10,
        })
        cls.pdf_data = base64.b64encode(
            open(misc.file_path('sign_oca/tests/empty.pdf'), 'rb').read()
        )

    def _new_event(self):
        return self.env['event.event'].create({
            'name': 'Evento contrato test',
            'event_type_id': self.event_type.id,
            'stage_id': self.draft_stage.id,
            'date_begin': '2026-06-01 22:00:00',
            'date_end': '2026-06-02 05:00:00',
            'seats_max': 300,
            'organizer_id': self.organizer.id,
            'fudo_event_analytic_account_id': self.event_analytic.id,
            'fudo_operation_analytic_account_id': self.operation_analytic.id,
        })

    def _generated_contract(self, event):
        attachment = self.env['ir.attachment'].create({
            'name': 'contrato.pdf',
            'type': 'binary',
            'datas': self.pdf_data,
            'res_model': 'event.event',
            'res_id': event.id,
            'mimetype': 'application/pdf',
        })
        contract = self.env['ponton.event.contract'].create({
            'name': 'Contrato test',
            'event_id': event.id,
            'body_html': '<h1>Contrato</h1>',
            'body_hash': 'body',
            'pdf_hash': 'pdf',
            'source_hash': 'pdf',
            'pdf_attachment_id': attachment.id,
            'state': 'generated',
        })
        event.write({
            'ponton_contract_id': contract.id,
            'ponton_contract_state': 'generated',
        })
        return contract

    def test_confirmed_stage_requires_signed_contract(self):
        event = self._new_event()
        with self.assertRaises(ValidationError):
            event.write({'stage_id': self.confirmed_stage.id})

        contract = self._generated_contract(event)
        contract.state = 'signed'
        event.write({'ponton_contract_state': 'signed'})
        event.write({'stage_id': self.confirmed_stage.id})
        self.assertEqual(event.stage_id, self.confirmed_stage)

    def test_stage_move_requires_event_type_before_contract_validation(self):
        event = self.env['event.event'].create({
            'name': 'Evento sin tipo',
            'date_begin': '2026-06-01 22:00:00',
            'date_end': '2026-06-02 05:00:00',
            'organizer_id': self.organizer.id,
            'fudo_event_analytic_account_id': self.event_analytic.id,
            'fudo_operation_analytic_account_id': self.operation_analytic.id,
        })
        with self.assertRaises(ValidationError):
            event.write({'stage_id': self.review_stage.id})

        event.write({
            'event_type_id': self.event_type.id,
            'stage_id': self.review_stage.id,
        })
        self.assertEqual(event.stage_id, self.review_stage)

    def test_create_with_explicit_stage_requires_event_type(self):
        with self.assertRaises(ValidationError):
            self.env['event.event'].create({
                'name': 'Evento creado en etapa',
                'stage_id': self.review_stage.id,
                'date_begin': '2026-06-01 22:00:00',
                'date_end': '2026-06-02 05:00:00',
                'organizer_id': self.organizer.id,
                'fudo_event_analytic_account_id': self.event_analytic.id,
                'fudo_operation_analytic_account_id': self.operation_analytic.id,
            })

    def test_critical_change_is_blocked_on_confirmed_signed_event(self):
        event = self._new_event()
        contract = self._generated_contract(event)
        contract.state = 'signed'
        event.write({
            'ponton_contract_state': 'signed',
            'stage_id': self.confirmed_stage.id,
        })
        with self.assertRaises(ValidationError):
            event.write({'ponton_contract_guest_count': 500})

    def test_organizer_contact_fields_are_partner_related(self):
        event = self._new_event()
        self.assertEqual(event.ponton_contract_organizer_id, event.organizer_id)
        self.assertEqual(event.ponton_contract_organizer_email, self.organizer.email)
        self.assertEqual(event.ponton_contract_organizer_phone, self.organizer.phone)
        self.assertEqual(event.ponton_contract_organizer_document, self.organizer.vat)

        event.ponton_contract_organizer_document = '30999888777'
        self.assertEqual(self.organizer.vat, '30999888777')

    def test_generate_contract_requires_complete_contract_data(self):
        organizer = self.env['res.partner'].create({
            'name': 'Productor Incompleto',
            'email': 'incompleto@example.com',
        })
        event = self.env['event.event'].create({
            'name': 'Evento incompleto',
            'event_type_id': self.event_type.id,
            'stage_id': self.draft_stage.id,
            'date_begin': '2026-06-03 22:00:00',
            'date_end': '2026-06-04 05:00:00',
            'organizer_id': organizer.id,
            'fudo_event_analytic_account_id': self.event_analytic.id,
            'fudo_operation_analytic_account_id': self.operation_analytic.id,
        })
        with self.assertRaisesRegex(ValidationError, 'Telefono del organizador'):
            event.action_ponton_generate_contract()

    def test_manso_signer_is_always_guido(self):
        event = self._new_event()
        event._ensure_contract_basics()
        self.assertEqual(event.ponton_contract_manso_partner_id, self.guido)

    def test_contract_required_can_come_from_operation_type(self):
        event_type = self.env['event.type'].create({'name': 'Sin contrato por tipo'})
        event = self.env['event.event'].create({
            'name': 'Evento contrato por operacion',
            'event_type_id': event_type.id,
            'stage_id': self.draft_stage.id,
            'date_begin': '2026-06-03 22:00:00',
            'date_end': '2026-06-04 05:00:00',
            'organizer_id': self.organizer.id,
            'fudo_event_analytic_account_id': self.event_analytic.id,
            'fudo_operation_analytic_account_id': self.operation_analytic.id,
        })
        self.assertTrue(event.ponton_contract_required)

    def test_legacy_organizer_migration_assistant(self):
        event = self.env['event.event'].create({
            'name': 'Evento legacy',
            'event_type_id': self.event_type.id,
            'stage_id': self.draft_stage.id,
            'date_begin': '2026-06-05 22:00:00',
            'date_end': '2026-06-06 05:00:00',
            'ponton_organizer_text': 'Productora Legacy',
            'ponton_contact_text': '+54 11 5555-4444',
            'fudo_event_analytic_account_id': self.event_analytic.id,
            'fudo_operation_analytic_account_id': self.operation_analytic.id,
        })
        wizard = self.env['ponton.event.organizer.migration.wizard'].create({})
        wizard.action_migrate()
        self.assertEqual(event.organizer_id.name, 'Productora Legacy')
        self.assertEqual(event.organizer_id.phone, '+54 11 5555-4444')

    def test_send_for_signature_is_idempotent_and_uses_visible_fields(self):
        event = self._new_event()
        contract = self._generated_contract(event)
        contract.action_send_for_signature()
        first_request = contract.sign_oca_request_id
        self.assertEqual(first_request.state, '0_sent')
        self.assertEqual(len(first_request.signer_ids), 2)
        data = first_request.signatory_data
        self.assertEqual({item['page'] for item in data.values()}, {1})
        organizer_item = data['1']
        self.assertEqual(organizer_item['position_x'], 10)
        self.assertEqual(organizer_item['position_y'], 82)
        self.assertEqual(organizer_item['width'], 30)
        self.assertEqual(organizer_item['height'], 8)

        contract.action_send_for_signature()
        self.assertEqual(contract.sign_oca_request_id, first_request)
        self.assertEqual(
            self.env['sign.oca.request'].search_count([('name', '=', contract.name)]),
            1,
        )

    def test_signed_request_sync_creates_signed_attachment(self):
        event = self._new_event()
        contract = self._generated_contract(event)
        contract.action_send_for_signature()
        request = contract.sign_oca_request_id
        request.write({'current_hash': 'signed-hash', 'state': '2_signed'})
        contract.invalidate_recordset()
        event.invalidate_recordset()
        self.assertEqual(contract.state, 'signed')
        self.assertEqual(event.ponton_contract_state, 'signed')
        self.assertEqual(contract.signed_hash, 'signed-hash')
        self.assertTrue(contract.signed_attachment_id)

    def test_cron_expires_unsigned_contracts(self):
        event = self._new_event()
        contract = self._generated_contract(event)
        contract.action_send_for_signature()
        contract.expires_at = fields.Datetime.subtract(fields.Datetime.now(), days=1)
        self.env['ponton.event.contract']._cron_expire_unsigned_contracts()
        contract.invalidate_recordset()
        event.invalidate_recordset()
        self.assertEqual(contract.state, 'expired')
        self.assertEqual(event.ponton_contract_state, 'expired')
        self.assertEqual(contract.sign_oca_request_id.state, '3_cancel')
