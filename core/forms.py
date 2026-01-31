from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(label=_("First name"), max_length=30, required=True, help_text=_('Required.'))
    last_name = forms.CharField(label=_("Last name"), max_length=30, required=True, help_text=_('Required.'))
    email = forms.EmailField(label=_("Email"), max_length=254, required=True, help_text=_('Required. Inform a valid email address.'))

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
