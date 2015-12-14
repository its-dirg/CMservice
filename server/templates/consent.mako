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

% if locked_claims:

<div style="clear: both;" class="locked_attr_div">
    <hr>
    <h3>${_("Locked attributes")}</h3>
    <p>${_("The following attributes is not optional. If you don't want to send these you need to abort.")}</p>
    % for attribute in locked_claims:
        <strong class="attr_header">${_(attribute).capitalize()}</strong>
        <br>
        <div class="locked_attribute">
            ${locked_claims[attribute] | list2str}
        </div>
    % endfor
</div>
% endif
<br>

<span style="float: left;">
    ${_("For how many month do you want to give consent for this particular service:")}
</span>
<br>

<form name="allow_consent" id="allow_consent_form" action="/save_consent" method="GET"
      style="float: left">
    <select name="month" id="month" class="dropdown-menu-right">
        % for month in months:
            <option value="${month}">${month}</option>
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

        var consent_status = $('#consent_status');

        var status = $("input[type=submit][clicked=true]").attr("name");
        consent_status.val(status);

        if (attributes.length == 0) {
            consent_status.val("No");
            alert("${_('No attributes where selected which equals no consent where given')}");
        }

        % for attr in locked_claims:
            attributes.push("${attr}");
        % endfor
        $('#attributes').val(attributes);

        this.submit(); // If all the validations succeeded
    });

    $("form input[type=submit]").click(function () {
        $("input[type=submit]", $(this).parents("form")).removeAttr("clicked");
        $(this).attr("clicked", "true");
    });
</script>