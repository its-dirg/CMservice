from cmservice.service.views import find_requester_name


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
