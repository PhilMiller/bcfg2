""" Handle encrypted Genshi templates (.crypt.genshi or .genshi.crypt
files) """

from Bcfg2.Compat import StringIO
from Bcfg2.Server.Plugins.Cfg.CfgGenshiGenerator import CfgGenshiGenerator
from Bcfg2.Server.Plugins.Cfg.CfgEncryptedGenerator import CfgEncryptedGenerator

try:
    from Bcfg2.Encryption import bruteforce_decrypt
except ImportError:
    # CfgGenshiGenerator will raise errors if crypto doesn't exist
    pass

try:
    from genshi.template import TemplateLoader
except ImportError:
    # CfgGenshiGenerator will raise errors if genshi doesn't exist
    TemplateLoader = object


class EncryptedTemplateLoader(TemplateLoader):
    """ Subclass :class:`genshi.template.TemplateLoader` to decrypt
    the data on the fly as it's read in using
    :func:`Bcfg2.Encryption.bruteforce_decrypt` """
    def _instantiate(self, cls, fileobj, filepath, filename, encoding=None):
        plaintext = StringIO(bruteforce_decrypt(fileobj.read()))
        return TemplateLoader._instantiate(self, cls, plaintext, filepath,
                                           filename, encoding=encoding)
        

class CfgEncryptedGenshiGenerator(CfgGenshiGenerator):
    """ CfgEncryptedGenshiGenerator lets you encrypt your Genshi
    :ref:`server-plugins-generators-cfg` files on the server """
    
    #: handle .crypt.genshi or .genshi.crypt files
    __extensions__ = ['genshi.crypt', 'crypt.genshi']

    #: Use a TemplateLoader class that decrypts the data on the fly
    #: when it's read in
    __loader_cls__ = EncryptedTemplateLoader
