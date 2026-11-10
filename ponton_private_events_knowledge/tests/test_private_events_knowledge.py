from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPontonPrivateEventsKnowledge(TransactionCase):
    def test_private_events_knowledge_pages_exist(self):
        root = self.env.ref('ponton_private_events_knowledge.category_private_events')
        self.assertEqual(root.type, 'category')

        pages = self.env['document.page'].search([('parent_id', '=', root.id)])
        self.assertEqual(len(pages), 11)
        self.assertTrue(all(page.type == 'content' for page in pages))
        self.assertTrue(all(page.content and page.content != '<p><br></p>' for page in pages))

        index = self.env.ref('ponton_private_events_knowledge.page_private_events_index')
        self.assertIn('Odoo es la fuente comercial', index.content)
        self.assertIn('Fudo es la fuente operativa', index.content)

    def test_private_events_knowledge_visibility_groups(self):
        operations = self.env.ref('ponton_knowledge_l10n.group_ponton_operations_manager')
        salon = self.env.ref('ponton_knowledge_l10n.group_ponton_salon')
        admin = self.env.ref('ponton_knowledge_l10n.group_ponton_admin')

        flow = self.env.ref('ponton_private_events_knowledge.page_private_events_flow')
        day = self.env.ref('ponton_private_events_knowledge.page_private_events_event_day')
        admin_close = self.env.ref('ponton_private_events_knowledge.page_private_events_odoo_close')

        self.assertIn(operations, flow.ponton_visibility_group_ids)
        self.assertIn(salon, day.ponton_visibility_group_ids)
        self.assertIn(admin, admin_close.ponton_visibility_group_ids)

