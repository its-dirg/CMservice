from unittest.mock import patch

from cmservice.service.views import find_requester_name, render_consent


class TestFindRequesterName(object):
    def test_should_find_exact_match(self):
        requester_name = [{'lang': 'sv', 'text': 'å ä ö'}, {'lang': 'en', 'text': 'aa ae oo'}]
        assert find_requester_name(requester_name, 'sv') == requester_name[0]['text']

    def test_should_fallback_to_english_if_available(self):
        requester_name = [{'lang': 'sv', 'text': 'å ä ö'}, {'lang': 'en', 'text': 'aa ae oo'}]
        assert find_requester_name(requester_name, 'unknown') == requester_name[1]['text']

    def test_should_fallback_to_first_entry_if_english_is_not_available(self):
        requester_name = [{'lang': 'sv', 'text': 'å ä ö'}, {'lang': 'no', 'text': 'Æ Ø Å'}]
        assert find_requester_name(requester_name, 'unknown') == requester_name[0]['text']


class TestRenderConsent(object):
    def test_locked_attr_not_contained_in_released_claims(self):
        with patch('cmservice.service.views.render_template') as m:
            render_consent('en', 'test_requester', ['foo', 'bar'], {'bar': 'test', 'abc': 'xyz'}, 'test_state',
                           [3, 6], True)

        locked_claims = {'bar': 'test'}
        released_claims = {'abc': 'xyz'}
        kwargs = m.call_args[1]
        assert kwargs['locked_claims'] == locked_claims
        assert kwargs['released_claims'] == released_claims
