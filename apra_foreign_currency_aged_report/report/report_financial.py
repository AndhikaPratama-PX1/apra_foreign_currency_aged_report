# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields, _
from odoo.tools.misc import format_date

from dateutil.relativedelta import relativedelta
from itertools import chain
import json
from odoo.tools.misc import formatLang, format_date

class ReportAccountAgedPartner(models.AbstractModel):
    _inherit = "account.aged.partner"

    filter_show_p_currency = True


    @api.model
    def _get_lines(self, options, line_id=None):
        self = self.with_context(report_options=options)

        line_dict = self._get_values(options=options, line_id=line_id)
        if line_id:  # prune the empty tree and keep only the wanted branch
            for key, value in self._parse_line_id(line_id):
                line_dict = line_dict['children'][(key, value)]
        if not line_dict['values']:
            return []

        lines = []
        self._append_grouped(
            lines=lines,
            current=self._parse_line_id(line_id),
            line_dict=line_dict,
            value_getters=[d.getter for d in self._get_column_details(options)[1:]],
            value_formatters=[d.formatter for d in self._get_column_details(options)[1:]],
            options=options,
            hidden_lines={},
        )

        if line_id:
            if options.get('lines_offset', 0):
                return lines[1:-1]  # TODO remove total line depending on param
            return lines  # No need to handle the total as we already only have pruned the tree
        if lines:
            # put the total line at the end or remove it
            result = lines[1:] 
            if options.get('show_p_currency'):
                result= result + (self.total_line and [{**lines[0], 'name': _('Total')}] or [])
            return result
        return []


    def _format_all_line(self, res, value_dict, options):

        if not options.get('show_p_currency') and value_dict.get('report_currency_id'):
            if value_dict.get('report_currency_id'):
                currency = self.env['res.currency'].browse(value_dict.get('report_currency_id')[0]).sudo()
                res['columns'][4]['name'] = self.format_value(res['columns'][4]['no_format'],currency)
                res['columns'][5]['name'] = self.format_value(res['columns'][5]['no_format'],currency)
                res['columns'][6]['name'] = self.format_value(res['columns'][6]['no_format'],currency)
                res['columns'][7]['name'] = self.format_value(res['columns'][7]['no_format'],currency)
                res['columns'][8]['name'] = self.format_value(res['columns'][8]['no_format'],currency)
                res['columns'][9]['name'] = self.format_value(res['columns'][9]['no_format'],currency)
                res['columns'][10]['name'] = self.format_value(res['columns'][10]['no_format'],currency)




    @api.model
    def _get_sql(self):
        options = self.env.context['report_options']
        if options.get('show_p_currency'):
            query = ("""
                SELECT
                    {move_line_fields},
                    account_move_line.partner_id AS partner_id,
                    partner.name AS partner_name,
                    COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                    COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                    account_move_line.payment_id AS payment_id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                    account_move_line.expected_pay_date AS expected_pay_date,
                    move.move_type AS move_type,
                    move.name AS move_name,
                    journal.code AS journal_code,
                    account.name AS account_name,
                    account.code AS account_code,""" + ','.join([("""
                    CASE WHEN period_table.period_index = {i}
                    THEN %(sign)s * ROUND((
                        account_move_line.balance - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0)
                    ) * currency_table.rate, currency_table.precision)
                    ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
                FROM account_move_line
                JOIN account_move move ON account_move_line.move_id = move.id
                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_account account ON account.id = account_move_line.account_id
                JOIN res_partner partner ON partner.id = account_move_line.partner_id
                LEFT JOIN ir_property trust_property ON (
                    trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                    AND trust_property.name = 'trust'
                    AND trust_property.company_id = account_move_line.company_id
                )
                JOIN {currency_table} ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.debit_move_id
                    FROM account_partial_reconcile part
                ) part_debit ON part_debit.debit_move_id = account_move_line.id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.credit_move_id
                    FROM account_partial_reconcile part
                ) part_credit ON part_credit.credit_move_id = account_move_line.id
                JOIN {period_table} ON (
                    period_table.date_start IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                )
                AND (
                    period_table.date_stop IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                )
                WHERE account.internal_type = %(account_type)s
                GROUP BY account_move_line.id, partner.id, trust_property.id, journal.id, move.id, account.id,
                         period_table.period_index, currency_table.rate, currency_table.precision
            """).format(
                move_line_fields=self._get_move_line_fields('account_move_line'),
                currency_table=self.env['res.currency']._get_query_currency_table(options),
                period_table=self._get_query_period_table(options),
            )
        else:
            query = ("""
                SELECT
                    {move_line_fields},
                    account_move_line.partner_id AS partner_id,
                    partner.name AS partner_name,
                    COALESCE(trust_property.value_text, 'normal') AS partner_trust,
                    COALESCE(account_move_line.currency_id, journal.currency_id) AS report_currency_id,
                    account_move_line.payment_id AS payment_id,
                    COALESCE(account_move_line.date_maturity, account_move_line.date) AS report_date,
                    account_move_line.expected_pay_date AS expected_pay_date,
                    move.move_type AS move_type,
                    move.name AS move_name,
                    journal.code AS journal_code,
                    account.name AS account_name,
                    account.code AS account_code,""" + ','.join([("""
                    CASE WHEN period_table.period_index = {i}
                    THEN %(sign)s * ROUND((
                        account_move_line.amount_currency - COALESCE(SUM(part_debit.amount), 0) + COALESCE(SUM(part_credit.amount), 0)
                    ) )
                    ELSE 0 END AS period{i}""").format(i=i) for i in range(6)]) + """
                FROM account_move_line
                JOIN account_move move ON account_move_line.move_id = move.id
                JOIN account_journal journal ON journal.id = account_move_line.journal_id
                JOIN account_account account ON account.id = account_move_line.account_id
                JOIN res_partner partner ON partner.id = account_move_line.partner_id
                LEFT JOIN ir_property trust_property ON (
                    trust_property.res_id = 'res.partner,'|| account_move_line.partner_id
                    AND trust_property.name = 'trust'
                    AND trust_property.company_id = account_move_line.company_id
                )
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.debit_move_id
                    FROM account_partial_reconcile part
                ) part_debit ON part_debit.debit_move_id = account_move_line.id
                LEFT JOIN LATERAL (
                    SELECT part.amount, part.credit_move_id
                    FROM account_partial_reconcile part
                ) part_credit ON part_credit.credit_move_id = account_move_line.id
                JOIN {period_table} ON (
                    period_table.date_start IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) <= DATE(period_table.date_start)
                )
                AND (
                    period_table.date_stop IS NULL
                    OR COALESCE(account_move_line.date_maturity, account_move_line.date) >= DATE(period_table.date_stop)
                )
                WHERE account.internal_type = %(account_type)s
                GROUP BY account_move_line.id, partner.id, trust_property.id, journal.id, move.id, account.id,
                         period_table.period_index
            """).format(
                move_line_fields=self._get_move_line_fields('account_move_line'),
                period_table=self._get_query_period_table(options),
            )
        params = {
            'account_type': options['filter_account_type'],
            'sign': 1 if options['filter_account_type'] == 'receivable' else -1,
        }
        return self.env.cr.mogrify(query, params).decode(self.env.cr.connection.encoding)




    def _get_hierarchy_details(self, options):
        if options.get('show_p_currency'):
            return [
                self._hierarchy_level('partner_id', foldable=True, namespan=5),
                self._hierarchy_level('id'),
            ]
        else:
            return [
                self._hierarchy_level('report_currency_id', foldable=False, namespan=5),
                self._hierarchy_level('partner_id', foldable=True, namespan=5),
                self._hierarchy_level('id'),
            ]

    def _format_report_currency_id_line(self, res, value_dict, options):
        obj = self.env['res.currency']
        curr_id = value_dict['report_currency_id'][0]
        curr = obj.browse(curr_id).sudo()
        res['name'] = curr.name
