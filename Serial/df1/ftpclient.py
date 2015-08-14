""" ******************************************************
Adapted from: An example of using the FTP client
              Copyright (c) Twisted Matrix Laboratories.
              See LICENSE for details.
****************************************************** """

# Twisted imports
from twisted.protocols.ftp import FTPClient, FTPFileListProtocol
from twisted.internet.protocol import Protocol, ClientCreator, ReconnectingClientFactory
from twisted.python import usage, logfile
from twisted.internet import reactor, defer, interfaces
from twisted.internet.task import LoopingCall
from twisted.protocols.basic import FileSender
from zope.interface import implements

import os

# Standard library imports
import string
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

    

class FTPClientA(FTPClient):
    """ **************************************************************
        Protocol subclass from FTPClient to add 'APPE' support allowing
        the ability to append data to a file.

    ************************************************************** """
    def __init__(self, factory, username = 'anonymous', password = 'anonymous@', passive = 1):
        FTPClient.__init__(self, username, password, passive)
        self.factory = factory
        self.debug = True

    def appendFile(self, path, offset=0):
        """ ******************************************************************
        Append to a file at the given path

        This method issues the 'APPE' FTP command

        @return: A Tuple of two L{Deferred}s:
                 -L{Deferred} L{IFinishableConsumer}. You must call
                  the C{finish} method on the IFinishableConsumer when the file
                  is completely transferred.
                 -L{Deferred} list of control-connection responses.
        ****************************************************************** """
        cmds = ['APPE ' + self.escapePath(path)]
        return self.sendToConnection(cmds)

    appe = appendFile



class FTPClientAFactory(ReconnectingClientFactory):

    protocol =  FTPClientA
    
    def buildProtocol(self, addr):
        self.resetDelay()

        p = FTPClientA(self, username='anonymous', password='anonymous@')
        p.factory = self
        self.connected = True
        return p

    def clientConnectionFailed(self, connector, reason):
        """ *******************************************************
        Called when a connection has failed to connect

        @type reason: L{twisted.python.fialure.Failure}
        ******************************************************* """
        print 'Connection fialed. Reason:', reason
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clienConnectionLost(self, connector, reason):
        """ **********************************************************
        Called when a connection has been lost after it was connected

        @type reason: L{twisted.python.fialure.Failure}
        ******************************************************* """
        print 'Lost Connection. Reason:', reason
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)


#---------------------------------------------------------------------------# 
# FTP Helper Functions
#---------------------------------------------------------------------------# 
# sendOEEData is used to send the local OEE data to a remote server
#
# getRecipeFiles is used to retrieve the most up to date recipe files.
# It does this by downloading the file 'families.csv' and then reading
# through that file and downloading each file that has an entry 
#
# cbStore is a helper function that acts as producer/consumer for the FTP
# file transfer. The consumer will be the remote file and the producer is
# the local file to be transferred.
#---------------------------------------------------------------------------# 

class FileReceiver(object):
    """
        Protocol subclass that writes received data to a local file.
    """
    implements(interfaces.IProtocol)
    
    def __init__(self, filename):
        self.fObj = None
        self.filename = filename

    def makeConnection(self, transport):
        self.fObj = open(self.filename, 'wb')

    def connectionLost(self, reason):
        self.fObj.close()

    def dataReceived(self, data):
        self.fObj.write(data)

def sendOEEData(ftpProtocol, localFile, remoteFile):
    # Attempt to send data accross FTP link
    print localFile, remoteFile
    d1, d2 = ftpProtocol.storeFile(remoteFile)
    d1.addCallback(cbStore, localFile)
    d1.addErrback(fail, "SendOEEData")
    return d2

def getRecipeFiles(ftpProtocol, localDir):
    def downloadRecipes(cmdDn):
        filename = localDir + '/' + 'families.csv'
        fObj = open(filename, 'r')
        print fObj
        for recipe in fObj:
            print recipe
            recipeName = recipe.strip()[0:8] + '.csv'
            recipeDir = localDir + recipeName 
            recipeFile = FileReceiver(recipeDir)
            d = ftpProtocol.retrieveFile(recipeName, recipeFile)
            d.addErrback(fail, "getRecipeFiles")

    # Download recipes
    familynames = localDir + '/families.csv'
    recipeFile = FileReceiver(familynames)
    d = ftpProtocol.retrieveFile('families.csv', recipeFile)
    d.addCallback(downloadRecipes)
    d.addErrback(fail, "getRecipeFiles")

def cbStore(consumer, filename):
    fs = FileSender()
    d = fs.beginFileTransfer(open(filename, 'r'), consumer)
    d.addCallback(lambda _: consumer.finish()).addErrback(fail, "cbStore")
    return d

def fail(error, msg=''):
    stringMsg = msg + ': Failed.  Error was: ', error, error.value
    print stringMsg
