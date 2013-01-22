########################################################################
# $HeadURL $
# File: FileCatalogProxyHandler.py
########################################################################

""" :mod: FileCatalogProxyHandler 
    ================================
 
    .. module: FileCatalogProxyHandler
    :synopsis: This is a service which represents a DISET proxy to the File Catalog    
"""
## imports
import os
from types import StringTypes, DictType, TupleType
## from DIRAC
from DIRAC import gLogger, gConfig, S_OK, S_ERROR
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC.Resources.Catalog.FileCatalog import FileCatalog
from DIRAC.Core.Utilities.Subprocess import pythonCall
from DIRAC.FrameworkSystem.Client.ProxyManagerClient import gProxyManager

__RCSID__ = "$Id$"

def initializeFileCatalogProxyHandler( serviceInfo ):
  """ service initalisation """ 
  return S_OK()

class FileCatalogProxyHandler( RequestHandler ):
  """
  .. class:: FileCatalogProxyHandler
  """

  types_callProxyMethod = [ StringTypes, StringTypes, TupleType, DictType ]
  def export_callProxyMethod( self, fcName, methodName, args, kargs ):
    """ A generic method to call methods of the Storage Element.
    """
    res = pythonCall( 0, self.__proxyWrapper, fcName, methodName, args, kargs )
    if res['OK']:
      return res['Value']
    else:
      return res

  def __proxyWrapper( self, fcName, methodName, args, kwargs ):
    """ The wrapper will obtain the client proxy and set it up in the environment.
        The required functionality is then executed and returned to the client.

    :param self: self reference
    :param str name: fcn name
    :param tuple args: fcn args
    :param dict kwargs: fcn keyword args 
    """
    res = self.__prepareSecurityDetails()
    if not res['OK']:
      return res
    try:
      fileCatalog = FileCatalog( [fcName] )
      method = getattr( fileCatalog, methodName )
    except AttributeError, error:
      errStr = "%sProxy: no method named %s" % ( fcName, methodName )
      gLogger.exception( errStr, methodName, error )
      return S_ERROR( errStr )
    try:
      result = method( *args, **kwargs )
      return result
    except Exception, error:
      errStr = "%sProxy: Exception while performing %s" % ( fcName, methodName )
      gLogger.exception( errStr, methodName, error )
      return S_ERROR( errStr )

  def __prepareSecurityDetails( self, vomsFlag = True ):
    """ Obtains the connection details for the client """
    try:
      credDict = self.getRemoteCredentials()
      clientDN = credDict[ 'DN' ]
      clientUsername = credDict['username']
      clientGroup = credDict['group']
      gLogger.debug( "Getting proxy for %s@%s (%s)" % ( clientUsername, clientGroup, clientDN ) )
      if vomsFlag:
        res = gProxyManager.downloadVOMSProxy( clientDN, clientGroup )
      else:
        res = gProxyManager.downloadProxy( clientDN, clientGroup )    
      if not res['OK']:
        return res
      chain = res['Value']
      proxyBase = "/tmp/proxies"
      if not os.path.exists( proxyBase ):
        os.makedirs( proxyBase )
      proxyLocation = "%s/%s-%s" % ( proxyBase, clientUsername, clientGroup )
      gLogger.debug( "Obtained proxy chain, dumping to %s." % proxyLocation )
      res = gProxyManager.dumpProxyToFile( chain, proxyLocation )
      if not res['OK']:
        return res
      gLogger.debug( "Updating environment." )
      os.environ['X509_USER_PROXY'] = res['Value']
      return res
    except Exception, error:
      exStr = "__getConnectionDetails: Failed to get client connection details."
      gLogger.exception( exStr, '', error )
      return S_ERROR( exStr )
