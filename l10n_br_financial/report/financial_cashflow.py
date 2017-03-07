# -*- coding: utf-8 -*-
# Copyright 2017 KMEE
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _, tools
from ..models.financial_move_model import (
    FINANCIAL_MOVE,
    FINANCIAL_STATE,
    FINANCIAL_TYPE
)


class FinancialCashflow(models.Model):

    _name = 'financial.cashflow'
    _auto = False

    cumulative_sum = fields.Monetary(
        string=u"Cumulative sum",
    )

    state = fields.Selection(
        selection=FINANCIAL_STATE,
        string='Status',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string=u'Company',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
    )
    document_number = fields.Char(
        string=u"Document Nº",
    )
    document_item = fields.Char(
        string=u"Document item",
    )
    document_date = fields.Date(
        string=u"Document date",
    )
    amount_document = fields.Monetary(
        string=u"Document amount",
    )
    due_date = fields.Date(
        string=u"Due date",
    )
    move_type = fields.Selection(
        selection=FINANCIAL_TYPE,
    )
    business_due_date = fields.Date(
        string='Business due date',
    )
    payment_mode = fields.Many2one(
        comodel_name='payment.mode',  # FIXME:
    )
    payment_term = fields.Many2one(
        comodel_name='payment.term',  # FIXME:
    )

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW financial_cashflow_credit_type_r as (
                SELECT * FROM (
                    SELECT
                        financial_move.create_date,
                        financial_move.id,
                        financial_move.document_number,
                        financial_move.document_item,
                        financial_move.move_type,

                        financial_move.state,
                        financial_move.business_due_date,
                        financial_move.document_date,
                        financial_move.payment_mode,
                        financial_move.payment_term,

                        financial_move.due_date,
                        financial_move.partner_id,
                        financial_move.currency_id,
                        financial_move.amount_document AS amount_document,
                        financial_move.amount_document AS credit_value,
                        0 AS debit_value
                    FROM
                        public.financial_move
                    WHERE
                        financial_move.move_type = 'r'
                ) r
            )
        """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW financial_cashflow_debit_type_p as (
                SELECT * FROM (
                    SELECT
                        financial_move.create_date,
                        financial_move.id,
                        financial_move.document_number,
                        financial_move.document_item,
                        financial_move.move_type,

                        financial_move.state,
                        financial_move.business_due_date,
                        financial_move.document_date,
                        financial_move.payment_mode,
                        financial_move.payment_term,

                        financial_move.due_date,
                        financial_move.partner_id,
                        financial_move.currency_id,
                        (-1) * financial_move.amount_document AS amount_document,
                        0 AS credit_value,
                        (-1) * financial_move.amount_document AS debit_value
                    FROM
                        public.financial_move
                    WHERE
                        financial_move.move_type = 'p'
                ) r
            )
        """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW financial_cashflow_main_view AS (
                SELECT
                    create_date, id, document_number, document_item, move_type,
                    state,
                    business_due_date,
                    document_date,
                    payment_mode,
                    payment_term,
                    due_date, partner_id, currency_id, amount_document,
                    SUM(credit_value),
                    SUM(debit_value)
                OVER (ORDER BY business_due_date)

                FROM (
                    SELECT * FROM financial_cashflow_credit_type_r
                    UNION
                    SELECT * FROM financial_cashflow_debit_type_p
                    ORDER BY business_due_date
                ) AS subq

                GROUP BY (create_date, id, document_number,
                    document_item, move_type,
                    state,
                    business_due_date,
                    document_date,
                    payment_mode,
                    payment_term,
                    due_date, partner_id, currency_id,
                    amount_document,
                    credit_value,
                    debit_value
		)
            )
        """)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW financial_cashflow AS (
                SELECT
                    create_date, id, document_number, document_item, move_type,
                    state,
                    business_due_date,
                    document_date,
                    payment_mode,
                    payment_term,
                    due_date, partner_id, currency_id, amount_document,
                    sum AS cumulative_sum

                    FROM (
                        SELECT * FROM financial_cashflow_main_view
                    ) AS out_format
            )
        """)
