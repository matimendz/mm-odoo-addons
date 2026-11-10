from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPontonPrivateEventFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.draft_stage = cls.env['event.stage'].create({'name': 'Privado borrador'})
        cls.confirmed_stage = cls.env['event.stage'].create({
            'name': 'Privado confirmado',
            'is_contract_confirmed_stage': True,
        })
        cls.final_stage = cls.env['event.stage'].create({'name': 'Finalizado'})
        cls.partner = cls.env['res.partner'].create({
            'name': 'Cliente Privado',
            'email': 'cliente@example.com',
            'phone': '3764000000',
            'vat': '30711111111',
        })
        cls.guido = cls.env['res.partner'].search([('email', '=ilike', 'guidoyamaguchi@gmail.com')], limit=1)
        if not cls.guido:
            cls.guido = cls.env['res.partner'].create({
                'name': 'Guido Yamaguchi',
                'email': 'guidoyamaguchi@gmail.com',
            })
        cls.event_analytic = cls.env['account.analytic.account'].create({
            'name': 'Evento privado test',
            'plan_id': cls.env.ref('ponton_fudo.analytic_plan_eventos').id,
        })
        cls.event_type = cls.env.ref('ponton_private_events.event_type_private_event')
        cls.operation = cls.env.ref('ponton_fudo.analytic_operation_evento_privado')

    def _private_event(self, **extra):
        vals = {
            'name': 'Cumpleanos privado test',
            'event_type_id': self.event_type.id,
            'stage_id': self.draft_stage.id,
            'date_begin': '2026-09-10 21:00:00',
            'date_end': '2026-09-11 05:00:00',
            'seats_max': 80,
            'organizer_id': self.partner.id,
            'fudo_event_analytic_account_id': self.event_analytic.id,
            'fudo_operation_analytic_account_id': self.operation.id,
            'ponton_private_event_type': 'birthday_50_plus',
            'ponton_private_commercial_model': 'package_per_person',
            'ponton_private_guest_mode': 'mixed',
            'ponton_private_guaranteed_guests': 80,
            'ponton_private_deposit_paid': True,
            'ponton_contract_required': True,
            'ponton_contract_kind': 'private_event',
        }
        vals.update(extra)
        return self.env['event.event'].create(vals)

    def test_lead_creates_private_event(self):
        lead = self.env['crm.lead'].create({
            'name': 'Casamiento Rio',
            'contact_name': 'Novios Test',
            'email_from': 'novios@example.com',
            'phone': '3764111111',
            'ponton_private_event_type': 'wedding',
            'ponton_private_tentative_date': '2026-10-01',
            'ponton_private_guest_count': 120,
            'ponton_private_guest_mode': 'seated',
        })
        lead.action_ponton_create_private_event()
        self.assertTrue(lead.ponton_private_event_id)
        self.assertEqual(lead.ponton_private_event_id.ponton_contract_kind, 'private_event')
        self.assertEqual(lead.ponton_private_event_id.fudo_operation_analytic_account_id, self.operation)
        self.assertLess(lead.ponton_private_event_id.date_begin, lead.ponton_private_event_id.date_end)

    def test_package_quote_generates_deposit(self):
        event = self._private_event()
        event.action_ponton_generate_private_quote()
        quote = event.ponton_private_quote_id
        self.assertTrue(quote)
        self.assertEqual(quote.ponton_private_commercial_model, 'package_per_person')
        self.assertGreater(quote.amount_total, 0)
        self.assertAlmostEqual(quote.ponton_private_deposit_amount, quote.amount_total * 0.30)

    def test_private_event_defaults_event_type(self):
        event = self.env['event.event'].create({
            'name': 'Evento privado sin tipo manual',
            'stage_id': self.draft_stage.id,
            'date_begin': '2026-09-10 21:00:00',
            'date_end': '2026-09-11 05:00:00',
            'seats_max': 80,
            'organizer_id': self.partner.id,
            'fudo_event_analytic_account_id': self.event_analytic.id,
            'ponton_private_event_type': 'corporate',
            'ponton_private_commercial_model': 'space_fee_plus_minimum_consumption',
            'ponton_private_guest_mode': 'mixed',
            'ponton_private_guaranteed_guests': 80,
        })
        self.assertEqual(event.event_type_id, self.event_type)
        self.assertEqual(event.ponton_contract_kind, 'private_event')

    def test_space_fee_quote_applies_rate_and_catering(self):
        event = self._private_event(
            ponton_private_commercial_model='space_fee_plus_minimum_consumption',
            ponton_private_season_band='high',
            ponton_private_catering_mode='external',
            date_begin='2026-11-13 21:00:00',
            date_end='2026-11-14 05:00:00',
        )
        event.action_ponton_generate_private_quote()
        self.assertEqual(event.ponton_private_space_fee, 600000)
        self.assertEqual(event.ponton_private_minimum_consumption, 400000)
        self.assertEqual(event.ponton_private_external_catering_fee, 150000)

    def test_package_quote_applies_external_catering_fee(self):
        event = self._private_event(ponton_private_catering_mode='external')
        event.action_ponton_generate_private_quote()
        self.assertEqual(event.ponton_private_external_catering_fee, 1500000)
        self.assertTrue(event.ponton_private_quote_id.order_line.filtered(
            lambda line: line.name == 'Recargo catering externo' and line.price_unit == 1500000
        ))

    def test_space_fee_quote_ignores_out_of_validity_rates(self):
        self.env.ref('ponton_private_events.rate_private_event_weekday').active = False
        self.env['ponton.private.event.rate'].create({
            'name': 'Tarifa vencida test',
            'season_band': 'medium',
            'day_type': 'weekday_sunday',
            'space_fee': 999999,
            'minimum_consumption': 999999,
            'valid_from': '2026-01-01',
            'valid_to': '2026-01-31',
        })
        self.env['ponton.private.event.rate'].create({
            'name': 'Tarifa vigente test',
            'season_band': 'medium',
            'day_type': 'weekday_sunday',
            'space_fee': 222000,
            'minimum_consumption': 111000,
            'valid_from': '2026-09-01',
            'valid_to': '2026-09-30',
        })
        event = self._private_event(
            ponton_private_commercial_model='space_fee_plus_minimum_consumption',
            ponton_private_season_band='medium',
            date_begin='2026-09-10 21:00:00',
            date_end='2026-09-11 05:00:00',
        )
        event.action_ponton_generate_private_quote()
        self.assertEqual(event.ponton_private_space_fee, 222000)
        self.assertEqual(event.ponton_private_minimum_consumption, 111000)

    def test_confirmed_private_event_requires_deposit_and_signed_contract(self):
        event = self._private_event(ponton_private_deposit_paid=False)
        with self.assertRaisesRegex(ValidationError, 'Contrato firmado'):
            event.write({'stage_id': self.confirmed_stage.id})

        contract = self.env['ponton.event.contract'].create({
            'name': 'Contrato privado test',
            'event_id': event.id,
            'body_html': '<h1>Contrato</h1>',
            'state': 'signed',
        })
        event.write({'ponton_contract_id': contract.id, 'ponton_contract_state': 'signed'})
        with self.assertRaisesRegex(ValidationError, 'Sena ingresada'):
            event.write({'stage_id': self.confirmed_stage.id})

        event.ponton_private_deposit_paid = True
        event.write({'stage_id': self.confirmed_stage.id})
        self.assertEqual(event.stage_id, self.confirmed_stage)

    def test_confirmed_private_event_keeps_deposit_invariant(self):
        event = self._private_event()
        contract = self.env['ponton.event.contract'].create({
            'name': 'Contrato privado test',
            'event_id': event.id,
            'body_html': '<h1>Contrato</h1>',
            'state': 'signed',
        })
        event.write({'ponton_contract_id': contract.id, 'ponton_contract_state': 'signed'})
        event.write({'stage_id': self.confirmed_stage.id})
        with self.assertRaisesRegex(ValidationError, 'Sena ingresada'):
            event.write({'ponton_private_deposit_paid': False})

    def test_private_contract_does_not_require_coproduction_economics(self):
        event = self._private_event()
        event.write({
            'ponton_contract_ponton_income': False,
            'ponton_contract_ponton_expense': False,
            'ponton_contract_organizer_income': False,
            'ponton_contract_organizer_expense': False,
        })
        event.action_ponton_generate_private_quote()
        event.action_ponton_generate_contract()
        self.assertTrue(event.ponton_contract_id)
        self.assertEqual(event.ponton_contract_id.state, 'generated')

    def test_blackout_blocks_without_override(self):
        with self.assertRaisesRegex(ValidationError, 'Fecha blackout'):
            self._private_event(date_begin='2026-07-20 21:00:00', date_end='2026-07-21 05:00:00')
        event = self._private_event(
            date_begin='2026-07-20 21:00:00',
            date_end='2026-07-21 05:00:00',
            ponton_private_allow_blackout_override=True,
        )
        event.ponton_private_allow_blackout_override = True
        event._check_private_event_constraints()

    def test_private_overrides_require_event_manager(self):
        event = self._private_event()
        user = self.env['res.users'].create({
            'name': 'Operador sin manager',
            'login': 'operador-privados@example.com',
            'email': 'operador-privados@example.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaisesRegex(ValidationError, 'manager de eventos'):
            event.with_user(user).write({'ponton_private_allow_balance_override': True})

    def test_expired_private_quote_requires_manager(self):
        event = self._private_event()
        event.action_ponton_generate_private_quote()
        quote = event.ponton_private_quote_id
        quote.ponton_private_quote_valid_until = fields.Date.subtract(fields.Date.today(), days=1)
        user = self.env['res.users'].create({
            'name': 'Comercial sin manager',
            'login': 'comercial-privados@example.com',
            'email': 'comercial-privados@example.com',
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('sales_team.group_sale_salesman_all_leads').id,
            ])],
        })
        with self.assertRaisesRegex(ValidationError, 'cotizacion privada vencio'):
            quote.with_user(user)._check_ponton_private_quote_validity()

    def test_checklist_blocks_finalization(self):
        event = self._private_event()
        event.action_ponton_generate_private_checklist()
        event.ponton_actual_attendee_count = 80
        with self.assertRaisesRegex(ValidationError, 'checklist critico'):
            event.write({'stage_id': self.final_stage.id})
        event.ponton_private_checklist_item_ids.filtered('is_critical').write({'done': True})
        event.write({'stage_id': self.final_stage.id})
        self.assertEqual(event.stage_id, self.final_stage)
