<%!
    def list2str(claim):
        # more human-friendly and avoid "u'" prefix for unicode strings in list
        if isinstance(claim, list):
            claim = ", ".join(claim)
        return claim
%>

<%inherit file="base.mako"/>

<%block name="head_title">Consent</%block>
<%block name="page_header">${_("Consent - Your consent is required to continue.")}</%block>
<%block name="extra_inputs">
    <input type="hidden" name="state" value="${ state }">
</%block>

## ${_(consent_question)}

<br>
<hr>

<div><b>${requester_name}</b> ${_("would like to access the following attributes:")}</div>
<br>

<div style="clear: both;">
    % for attribute in released_claims:
        <strong>${_(attribute).capitalize()}</strong><br><pre>    ${released_claims[attribute] | list2str}</pre>
    % endfor
</div>
<br>

<form name="allow_consent" action="/save_consent" method="GET"
      style="float: left">
    <button name="ok" value="Yes" id="submit_ok" type="submit">${_('Ok, accept')}</button>
    ${extra_inputs()}
</form>
<form name="deny_consent" action="/save_consent" method="GET"
      style="float: left; clear: right;">
    <button name="ok" value="No" id="submit_deny" type="submit">${_('No, cancel')}</button>
    ${extra_inputs()}
</form>
<br>
<br>