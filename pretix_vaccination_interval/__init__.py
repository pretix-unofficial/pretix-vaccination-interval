from django.utils.translation import gettext_lazy

try:
    from pretix.base.plugins import PluginConfig
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")

__version__ = '1.0.0'


class PluginApp(PluginConfig):
    name = 'pretix_vaccination_interval'
    verbose_name = 'Enforced vaccination intervals'

    class PretixPluginMeta:
        name = gettext_lazy('Enforced vaccination intervals')
        author = 'pretix team'
        description = gettext_lazy('If pretix is used for COVID-19 vaccinations, this plugin can be used to make sure the correct number of days between two shots is ensured.')
        visible = True
        experimental = True
        version = __version__
        category = 'CUSTOMIZATION'
        compatibility = "pretix>=2.7.0"

    def ready(self):
        from . import signals  # NOQA


default_app_config = 'pretix_vaccination_interval.PluginApp'
