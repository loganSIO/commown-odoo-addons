import os.path as osp
import json
import logging

from odoo.addons.payment_slimpay.models import slimpay_utils


_logger = logging.getLogger(__name__)


# Low level helpers ###########################################################

def mandate_doc_ref(acquirer, mandate_doc):
    "Return the reference of the mandate supplied as an HAPI representation"
    return mandate_doc['reference']


def get_partner(acquirer, mandate_doc):
    subscriber_url = mandate_doc[
        acquirer.slimpay_client.method_name('get-subscriber')].url
    pid = subscriber_url.rsplit('/', 1)[-1]
    if pid.isdigit:
        return acquirer.env['res.partner'].search([
            ('id', '=', int(pid)),
        ])
    else:
        return acquirer.env['res.partner'].search([
            ('payment_token_id.acquirer_ref', '=', mandate_doc['id']),
        ])


def mandate_doc_to_repr(acquirer, mandate_doc):
    """Return a json representation of the supplied HAPI mandate doc that
    is suitable for creating a copy using the `create-mandates` HAPI call.
    """
    partner = get_partner(acquirer, mandate_doc)
    bank_account_doc = acquirer.slimpay_client.action(
        'GET', 'get-bank-account', doc=mandate_doc)
    if partner:
        signatory = slimpay_utils.subscriber_from_partner(partner)['signatory']
        signatory['bankAccount'] = {
            'bic': bank_account_doc['bic'],
            'iban': bank_account_doc['iban'],
        }
        return {
            'reference': mandate_doc['reference'],
            'dateSigned': mandate_doc['dateSigned'],
            'createSequenceType': 'FRST',
            'subscriber': {'reference': partner.id},
            'signatory': signatory,
        }


def get_all_mandates_repr(acquirer, transformer_func, **params):
    """Query Slimpay API's `acquirer` account for all mandates with
    optional search criteria `params` and return them after applying
    the given transformer function.
    """
    client = acquirer.slimpay_client
    params['creditorReference'] = acquirer.slimpay_creditor
    _logger.debug(u'Fetching first mandates...')
    doc = client.action('GET', 'search-mandates', params=params)
    if 'mandates' in doc:
        for mandate_doc in doc['mandates']:
            result = transformer_func(acquirer, mandate_doc)
            if result:
                yield result
        page_num = doc['page']['totalPages']
        for page in range(1, page_num):
            _logger.debug(u'Fetching page %d / %d...', page+1, page_num)
            doc = client.get(doc.links['next'].url)
            for mandate_doc in doc['mandates']:
                result = transformer_func(acquirer, mandate_doc)
                if result:
                    yield result


def create_and_set_mandate(acquirer, mandate_repr):
    """ Create a mandate using supplied description `mandate_repr` in given
    `acquirer`'s context and set it as default mandate for the partner pointed
    to as the subscriber `mandate_repr`.
    """
    mandate_repr['creditor'] = {'reference': acquirer.slimpay_creditor}
    new_mandate_doc = acquirer.slimpay_client.action(
        'POST', 'create-mandates', params=mandate_repr)
    Partner = acquirer.env['res.partner']
    partner = Partner.browse(mandate_repr['subscriber']['reference']).exists()
    partner.payment_token_id.update({
        'acquirer_ref': new_mandate_doc['id'],
        'acquirer_id': acquirer.id,
    })
    return new_mandate_doc


def set_contract_for_invoice_merge_autopay(contract):
    """ Update contract and related partner so that the merge invoice
    mecanism is used instead of contract_payment_auto module's
    mecanism to pay all the partner's draft invoices at once using a
    merged invoice if necessary.
    """
    assert contract.is_auto_pay and contract.recurring_invoices
    contract.is_auto_pay = False
    partner = contract.partner_id

    if partner.invoice_merge_reference_date:
        next_date = max(partner.invoice_merge_reference_date,
                        contract.recurring_next_date)
        if next_date != contract.recurring_next_date:
            _logger.debug(u'%s %s -> %s (%s)',
                          contract.name, contract.recurring_next_date,
                          next_date, partner.name)
    else:
        next_date = contract.recurring_next_date

    partner.update({
        'invoice_merge_reference_date': next_date,
        'invoice_merge_recurring_rule_type': 'monthly',
        'invoice_merge_recurring_interval': 1,
        'invoice_merge_next_date': next_date,
    })


def replace_mandate(acquirer, mandate_repr):
    """ Replace partner's mandate by a new one described by `mandate_repr`
    in the context of give `acquirer`.
    """
    partner = acquirer.env['res.partner'].browse(
        mandate_repr['subscriber']['reference'])
    # Fix wrong data for companies and missing country
    if partner.is_company:
        mandate_repr['signatory']['givenName'] = '-'
    if mandate_repr['signatory']['billingAddress']['country'] is None:
        _logger.debug(
            u'WARNING! No country set for %s. Assuming FR. Please fix data.',
            partner.name)
        mandate_repr['signatory']['billingAddress']['country'] = 'FR'

    new_mandate_doc = create_and_set_mandate(acquirer, mandate_repr)
    _logger.debug(
        u'Created new mandate %s for %s', new_mandate_doc['reference'],
        partner.name)


# High level helpers ##########################################################

def dump_all_mandates(acquirer, refresh, mandates_fpath, **params):
    """ Extract all mandates and dump them as a json descr in `mandates_fpath`
    If the `refresh` parameter is True (the default), try to read given file
    for a previous mandate list and only append newly signed mandates.
    """

    old_mandates = []

    if refresh and osp.isfile(mandates_fpath):
        with open(mandates_fpath) as fobj:
            old_mandates = json.load(fobj)
            if old_mandates:
                params['dateSignedAfter'] = max(
                    m['dateSigned'] for m in old_mandates)

    mandates = old_mandates + list(
        get_all_mandates_repr(acquirer, mandate_doc_to_repr, **params))
    json.dump(mandates, open(mandates_fpath, 'wb'))


def restore_all_missing_mandates(
        acquirer, mandates_fpath='/tmp/mandates.json', **params):
    " Restore all mandates from production to preproduction environment "

    mandates_repr = json.load(open(mandates_fpath))
    known_mandate_refs = set(get_all_mandates_repr(
        acquirer, mandate_doc_ref, **params))
    for mandate_repr in mandates_repr:
        mandate_repr['reference'] = 'TEST' + mandate_repr['reference'][4:]
        if mandate_repr['reference'] not in known_mandate_refs:
            replace_mandate(acquirer, mandate_repr)
        else:
            partner = acquirer.env['res.partner'].browse(
                mandate_repr['subscriber']['reference'])
            _logger.debug('No need to create mandate for %s: already done',
                          partner.name)

    acquirer.env.cr.commit()
