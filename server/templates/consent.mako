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
        <strong>${_(attribute).capitalize()}</strong>
        <br>

        <div class="attribute">
            <input type="checkbox"
                   name="${attribute.lower()}"
                   value="${released_claims[attribute] | list2str}"
                   checked>
            ${released_claims[attribute] | list2str}
        </div>
    % endfor
</div>
<br>

<span style="float: left;">
    ${_("I which point in time do you want to give consent again for this particular service:")}
</span>
<br>

<form name="allow_consent" id="allow_consent_form" action="/save_consent" method="GET"
      style="float: left">
    <select name="policy" id="policy" class="dropdown-menu-right">
        % for policy in policies:
            <option value="${policy}">${_(policy.lower())}</option>
        % endfor
    </select>
    <br>
    <br>
    <input name="Yes" value="${_('Ok, accept')}" id="submit_ok" type="submit">
    <input name="No" value="${_('No, cancel')}" id="submit_deny" type="submit">

    <input type="hidden" id="attributes" name="attributes"/>
    <input type="hidden" id="consent_status" name="consent_status"/>
    ${extra_inputs()}
</form>
<br>
<br>
<br>

<script>
    $('input:checked').each(function () {
        if (!${select_attributes.lower()}) {
            $(this).removeAttr("checked")
        }
    });

    $('#allow_consent_form').submit(function (ev) {
        ev.preventDefault(); // to stop the form from submitting

        var attributes = [];
        $('input:checked').each(function () {
            attributes.push(this.name);
        });

        $('#attributes').val(attributes);
        var status = $("input[type=submit][clicked=true]").attr("name");
        $('#consent_status').val(status);

        if (attributes.length == 0) {
            $('#consent_status').val("No");
            alert("${_('No attributes where selected which equals no consent where given')}");
        }

        this.submit(); // If all the validations succeeded
    });

    $("form input[type=submit]").click(function () {
        $("input[type=submit]", $(this).parents("form")).removeAttr("clicked");
        $(this).attr("clicked", "true");
    });
</script>