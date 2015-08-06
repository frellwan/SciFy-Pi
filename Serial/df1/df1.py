#!/usr/bin/env python
'''
Asynchronous Processor Example
--------------------------------------------------------------------------

The following is a full example of a continuous client processor. Feel
free to use it as a skeleton guide in implementing your own.
'''
#---------------------------------------------------------------------------# 
# import the neccessary modules
#---------------------------------------------------------------------------# 
from twisted.internet import serialport, reactor
from twisted.internet.protocol import ClientFactory
from factory import ClientDecoder
from twisted.internet import defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from transaction import SocketFramer
from twisted.internet.task import LoopingCall
from twisted.python import logfile, log
from twisted.protocols.basic import FileSender
from twisted.protocols.ftp import FTPClient, FTPFileListProtocol
from twisted.python import usage, logfile
from ConfigParser import SafeConfigParser
import utilities
from async import SerialClientProtocol
from emailclient import sendEmail
from ftpclient import *
from df1commands import *
from loggerfile import *
from serialexceptions import ConnectionException

import string
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from loggerfile import *
import time
import os

import struct


#---------------------------------------------------------------------------# 
# Choose the framer you want to use
#---------------------------------------------------------------------------# 
#from pymodbus.transaction import ModbusBinaryFramer as ModbusFramer
#from pymodbus.transaction import ModbusAsciiFramer as ModbusFramer
#from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
#from DF1.transaction import DF1Framer as DF1Framer

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
serialLog = logging.getLogger("SerialMaster")
serialLog.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# state a few constants
#---------------------------------------------------------------------------# 
TIMEOUT = 1
MAXENQ = 3



#---------------------------------------------------------------------------# 
# an example custom protocol
#---------------------------------------------------------------------------# 
# Here you can perform your main procesing loop utilizing defereds and timed
# callbacks.
#---------------------------------------------------------------------------# 
class DF1ClientProtocol(SerialClientProtocol):

    def __init__(self, logger, ftpEndpoint):
        ''' Initializes our custom protocol

        :param logger: The local file to store results
        :param ftpEndpoint: The endpoint to send results to and read recipes from
        '''
        SerialClientProtocol.__init__(self)
        self.logger = logger
        self.ftpEndpoint = ftpEndpoint
        self.logFile = logger.getFileName()
        self.ENQCount = 0
        self.lcOEE = LoopingCall(self.startOEEData)
        self.lcAlarms = LoopingCall(self.startAlarmsData)
        self.lcFTP = LoopingCall(self.startFTPTransfer)
        self._reconnecting = False
        self.config = utilities.optionReader()
        log.startLogging(sys.stdout)
        self.notified = False
        self.transferred = False
        self.loaded = False


    def connectionMade(self):
        ''' Called upon a successful client connection.
        '''
        self._connected = True
        serialLog.debug("Client connected to DF1 server")
        self.VARIABLES = self.config.getPLCVariables()
        self.ALARMS = self.config.getPLCAlarms()
        self.localLogDir, self.remoteLogDir = self.config.getFTPDirectories()

        self.lcOEE.start(self.config.getOEETime())
        self.lcAlarms.start(self.config.getAlarmTime())
        self.lcFTP.start(self.config.getFTPTime())

    def connectionLost(self, reason):
        ''' Called upon a client disconnect

        :param reason: The reason for the disconnect
        '''
        serialLog.debug("Client disconnected from DF1 server: %s" % reason)
        self.lcOEE.stop()
        self.lcAlarms.stop()
        self.lcFTP.stop()
        self._connected = False
        #for tid in self.transaction:
        #    self.transaction.getTransaction(tid).errback(Failure(
        #        ConnectionException('Connection lost during request')))
        self.reconnect()

    def reconnect(self):
        try:
            RS232port, RS232baud = self.config.getRS232parms()
            serialport.SerialPort(self, RS232port, reactor, baudrate = RS232baud)
            serialLog.debug("RECONNECTED")

        except:
            serialLog.debug("Error opening serial port...", sys.exc_info()[1])
            self.retry = reactor.callLater(5.31, self.reconnect)

    def startFTPTransfer(self):
        d = self.ftpEndpoint.connect(FTPClientAFactory())
        d.addCallback(sendOEEData,os.path.join(self.localLogDir, self.logFile), os.path.join(self.remoteLogDir, self.logFile))
        d.addErrback(self.FTPfail, 'startFTPTransfer')
        if (self.logger.getFileName() != self.logFile):
            self.logFile = self.logger.getFileName()
            #reactor.callLater(17.23,self.startFTPTransfer)

    def startAlarmsData(self):
        var = []

        for address in self.ALARMS:
            request = protectedReadRequest(1, address)
            result = self.sendRequest(request)
            var.append(result)

        d = defer.gatherResults(var)
        d.addCallback(self.evaluateBits)
        d.addErrback(self.errorHandler, 'gather results in startAlarmsData')
       
    def startOEEData(self):
        var = []

        for address in self.VARIABLES:
            request = protectedReadRequest(1, address)
            result = self.sendRequest(request)
            var.append(result)
        d = defer.gatherResults(var)
        d.addCallback(self.logger.write)
        d.addErrback(self.errorHandler, 'saving data in StartOEEData failed')

    def ackPacket(self, packet):
        #ACK Message, reset counters/timers and release lock to prepare for next message
        self.transport.write('\x10\x06')
        self.resetTimeout()
        self.ENQCount = 0
        self.NAKCount = 0
        self.setTimeout(None)
        self.deffered = None
        
        return packet.records

    def evaluateBits(self, alarmBits):
        bits = utilities.flatten(alarmBits)
        if (bits[0]):
            # self.notified added so multiple emails won't be sent
            if (not self.notified):
                serialLog.debug("Sending Email notice of Error")
                strMsg = ''
                if (bits[0] & 1):
                    """ Temperature Too High Alarm """
                    strMsg += "Temperature has reached a critical point\n"

                if (bits[0] & 2):
                    """ Motor Amps exceeded threshold """
                    strMsg += "TU Motor Current has exceeded baseline threshold\n"

                if (bits[0] & 4):
                    """ Vibration exceeds threshold """
                    strMsg += "Vibration sensor readings outside of acceptable tolerance\n"

                if (bits[0] & 8):
                    """ Speed variance outside of tolerance """
                    strMsg += "TU speed is varying more than specified tolerance\n"

                sender, recepient = self.config.getEmail()
                sendEmail(sender, recepient, strMsg, "Alert: Alarm")
                self.notified = True
        else:
            self.notified = False

        if (bits[1]):
            # self.loaded added so multiple uploads won't be initiated
            # TODO: Add code to load values to PLC
            if (not self.loaded):
                serialLog.debug("Loading Values to PLC")
                print "Load values to PLC"
                """
                Get Recipe Name From PLC
                Read Recipe File to get Values
                Load Values to PLC
                Clear bit
                """
                self.loaded = True
        else:
            self.loaded = False
            

        if (bits[2]):
            # self.transferred added so multiple downloads won't be initiated
            if (not self.transferred):
                #Download Recipes from Server
                localDir, remoteDir = self.config.getRecipeDirectories()
                serialLog.debug("Downloading Recipes")
                d = self.ftpEndpoint.connect(FTPClientAFactory())
                d.addCallback(getRecipeFiles, localDir)
                d.addErrback(self.FTPfail, 'startFTPTransfer')
                self.transferred = True
        else:
            self.transferred = False
            
    def FTPfail(self, error, msg):
        stringMsg = msg + ': Failed.  Error was: %s' % error.type
        serialLog.debug(stringMsg)
        #Network Down, Try again periodically.
        #TODO: Check if the logFile name has changed while network down
        #      to make sure we get all files that have been missed
        #reactor.callLater(17.23, self.startFTPTransfer)

       

#---------------------------------------------------------------------------# 
# a factory for the example protocol
#---------------------------------------------------------------------------# 
# This is used to build client protocol's if you tie into twisted's method
# of processing. It basically produces client instances of the underlying
# protocol::
#
#     Factory(Protocol) -> ProtocolInstance
#
# It also persists data between client instances (think protocol singelton).
#---------------------------------------------------------------------------# 
class DF1Factory(ClientFactory):

    protocol = DF1ClientProtocol

    def __init__(self, logger, endpoint):
        ''' Remember things necessary for building a protocols '''
        self.logger = logger
        self.endpoint = endpoint

    def buildProtocol(self):
        ''' Create a protocol and start the reading cycle '''
        proto = self.protocol(self.logger, self.endpoint)
        proto.factory = self
        return proto


#---------------------------------------------------------------------------# 
# a custom client for our device
#---------------------------------------------------------------------------# 
# Twisted provides a number of helper methods for creating and starting
# clients:
# - protocol.ClientCreator
# - reactor.connectTCP
#
# How you start your client is really up to you.
#---------------------------------------------------------------------------# 
class SerialDF1Client(serialport.SerialPort):

    def __init__(self, factory, *args, **kwargs):
        ''' Setup the client and start listening on the serial port

        :param factory: The factory to build clients with
        '''
        protocol = factory.buildProtocol()
        self.decoder = ClientDecoder()
        serialport.SerialPort.__init__(self, protocol, *args, **kwargs)


#---------------------------------------------------------------------------# 
# a custom endpoint for our results
#---------------------------------------------------------------------------# 
#---------------------------------------------------------------------------# 
class LoggingLineWriter(object):
    def __init__(self, logDir):
        self.logPath = logDir
        t = time.localtime()[:3]
        self.fileName = '%02d%02d%02d00.csv' % (t[0]-100*(int(t[0]/100)), t[1], t[2])      
        self.logFile = DailyLogger(self.fileName, self.logPath)

    def getFileName(self):
        return self.fileName

    def write(self, response):
        ''' Write the data to the specified file

        :param response: The response to process
        '''
        data = []
        for item in response:
            data.append(item)
        response = utilities.flatten(data)
        currentTime = time.localtime()
        stringData = time.strftime('%m/%d/%Y,', currentTime)
        stringData += time.strftime('%T,', currentTime)
        stringData += ','.join(map(str, response))
        stringData += '\n'
        logName = self.logFile.write(stringData)
        if (self.fileName != logName):
            self.fileName = logName


#---------------------------------------------------------------------------# 
# start running the processor
#---------------------------------------------------------------------------# 
# This initializes the client, the framer, the factory, and starts the
# twisted event loop (the reactor). 
#---------------------------------------------------------------------------# 
def main():
    serialLog.debug("Initializing the client")

    config = utilities.optionReader()

    print config.getFTPDirectories()
    localDir, remoteDir = config.getFTPDirectories()
    oeeLog = LoggingLineWriter(localDir)
    
    # Create the FTP client
    FTPhost, FTPport = config.getFTPparms()
    ftpEndpoint = TCP4ClientEndpoint(reactor, FTPhost, FTPport)

    RS232port, RS232baud = config.getRS232parms()

    factory = DF1Factory(oeeLog, ftpEndpoint)
    
    SerialDF1Client(factory, RS232port, reactor, baudrate = RS232baud)

    serialLog.debug("Starting the client")
    reactor.run()


if __name__ == "__main__":
    main()
