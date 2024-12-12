from django import forms

class SalesReportForm(forms.Form):
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=True)
    report_type = forms.ChoiceField(choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom Date Range')
    ])
