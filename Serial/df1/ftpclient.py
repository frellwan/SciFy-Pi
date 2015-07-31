""" ******************************************************
Adapted from: An example of using the FTP client
              Copyright (c) Twisted Matrix Laboratories.
              See LICENSE for details.
****************************************************** """

# Twisted imports
from twisted.protocols.ftp import FTPClient, FTPFileListProtocol
from twisted.internet.protocol import Protocol, ClientCreator, ClientFactory
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



class FTPClientAFactory(ClientFactory):

    protocol =  FTPClientA
    
    def buildProtocol(self, addr):
        #self.resetDelay()

        p = FTPClientA(self, username='anonymous', password='anonymous@')
        p.factory = self
        self.connected = True
        return p

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

class BufferingProtocol(Protocol):
    """Simple utility class that holds all data written to it in a buffer."""
    def __init__(self):
        self.buffer = StringIO()

    def dataReceived(self, data):
        self.buffer.write(data)

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
    #print "Connection Made"

    # Attempt to send data accross FTP link
    d1, d2 = ftpProtocol.storeFile(remoteFile)
    d1.addCallback(cbStore, localFile)
    d1.addErrback(fail, "SendOEEData")
    return d2

def getRecipeFiles(ftpProtocol):
    def downloadRecipes(self):
        fObj = open('./recipes/families.csv', 'r')
        for recipe in fObj:
            recipeName = recipe.strip() + '.csv'
            recipeDir = './recipes/' + recipeName 
            recipeFile = FileReceiver(recipeDir)
            d = ftpProtocol.retrieveFile(recipeName, recipeFile)
            d.addErrback(fail, "getRecipeFiles")

    # Change to the parent directory
    recipeFile = FileReceiver('./recipes/families.csv')
    d = ftpProtocol.retrieveFile('families.csv', recipeFile)
    d.addCallback(downloadRecipes)
    d.addErrback(fail, "getRecipeFiles")

    # Create a buffer
    proto = BufferingProtocol()

    # Get short listing of current directory, and quit when done
    #d = ftpClient.nlst('.', proto)
    #d.addCallbacks(showBuffer, fail, callbackArgs=(proto,))    

def cbStore(consumer, filename):
    fs = FileSender()
    d = fs.beginFileTransfer(open(filename), consumer)
    d.addCallback(lambda _: consumer.finish()).addErrback(fail, "cbStore")
    return d

def showBuffer(result, bufferProtocol):
    print 'Got data:'
    print bufferProtocol.buffer.getvalue()

def fail(error, msg=''):
    stringMsg = msg + ': Failed.  Error was: ', error, error.value
    print stringMsg
    #serialLog.debug(stringMsg)
    #sendEmail('4137@commscope.com', 'erice@commscope.com', stringMsg, 'RPi SerialMaster Error')

def success(response):
    print 'Success!  Got response:'
    print '---'
    if response is None:
        print None
    else:
        print string.join(response, '\n')
    print '---'


