from django import forms
from .models import Bundle, Buyer, Lay, SpecRow, Style, WorkOrder

class BuyerForm(forms.ModelForm):
    class Meta:
        model = Buyer
        fields = ["name", "code", "default_sizeset", "notes"]

class StyleForm(forms.ModelForm):
    class Meta:
        model = Style
        fields = ["buyer", "category", "style_code", "name", "sizeset"]

    def __init__(self, *a, buyer_qs=None, **k):
        super().__init__(*a, **k)
        if buyer_qs is not None:
            self.fields["buyer"].queryset = buyer_qs

class SpecRowForm(forms.ModelForm):
    class Meta:
        model = SpecRow
        fields = ["target_mm", "tol_plus_mm", "tol_minus_mm"]

class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = ["buyer", "style", "po_number", "delivery_date"]

    def __init__(self, *a, style_qs=None, **k):
        super().__init__(*a, **k)
        if style_qs is not None:
            self.fields["style"].queryset = style_qs

class LayForm(forms.ModelForm):
    class Meta:
        model = Lay
        fields = ["lay_number", "fabric_batch", "shade", "plies", "shrinkage_band_mm"]

class BundleForm(forms.Form):
    lines = forms.CharField(
        widget=forms.Textarea,
        help_text="one per line: SIZE, QTY  (e.g. M, 20)"
    )
