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
from twisted.internet import defer
from twisted.internet.task import LoopingCall
from async import SerialClientProtocol
from factory import ClientDecoder
from MTrimCommands import *
from ConfigParser import SafeConfigParser
from twisted.python import usage, logfile

#---------------------------------------------------------------------------# 
# Choose the framer you want to use
#---------------------------------------------------------------------------# 
#from transaction import BinaryFramer
from transaction import AsciiFramer 
#from transaction import ModbusRtuFramer
#from transaction import SocketFramer

#---------------------------------------------------------------------------# 
# configure the client logging
#---------------------------------------------------------------------------# 
import logging
logging.basicConfig()
log = logging.getLogger("MTrim Serial")
log.setLevel(logging.DEBUG)

#---------------------------------------------------------------------------# 
# state a few constants
#---------------------------------------------------------------------------# 
CLIENT_DELAY = 1

class Options(usage.Options):
    optParameters = [['config', 'c', './config.ini']]

#---------------------------------------------------------------------------# 
# an example custom protocol
#---------------------------------------------------------------------------# 
# Here you can perform your main procesing loop utilizing defereds and timed
# callbacks.
#---------------------------------------------------------------------------# 
class MTrimProtocol(SerialClientProtocol):

    def __init__(self, framer):
        ''' Initializes our custom protocol

        :param framer: The framer to use to process incoming messages
        '''
        SerialClientProtocol.__init__(self, framer)
        self.parameter = 1
        self._connected = False
        log.debug("Beginning the processing loop")

    def connectionMade(self):
        ''' Called upon a successful client connection.
        '''
        log.debug("Client connected to Serial server")
        self._connected = True
        reactor.callLater(CLIENT_DELAY, self.sendMessage)

    def reconnect(self):
        try:
            options = Options()
            config = SafeConfigParser()
            config.read([options['config']])
            serialport.SerialPort(self, config.get('RS-422', 'host'), reactor, baudrate = config.getint('RS-422', 'baudrate'))
            if self.deferred:
                self.deferred = None
                self.lock.release()

        except:
            log.debug("Error opening serial port...")
            self.retry = reactor.callLater(5.31, self.reconnect)

    def readParameter(self, address, parameter, **kwargs):
        '''

        :param address: The starting address to read from
        :param parameter: The parameter number to write to
        :returns: A deferred response handle
        '''
        request = DataInquiryRequest(address, parameter, **kwargs)
        return self.sendRequest(request)

    def writeParameter(self, address, parameter, value, **kwargs):
        '''

        :param address: The starting address to read from
        :param parameter: The parameter number to write to
        :param value: The value to write to the parameter
        :returns: A deferred response handle
        '''
        request = ParameterSendRequest(address, parameter, value, **kwargs)
        return self.sendRequest(request)

    def controlCommand(self, address, value, **kwargs):
        '''

        :param address: The starting address to write to
        :param value: The value to write to the specified address
        :param unit: The slave unit this request is targeting
        :returns: A deferred response handle
        '''
        request = ControlCommandSendRequest(address, value, **kwargs)
        return self.execute(request)

    def sendMessage(self):
        ''' Defer fetching holding registers
        '''
        if self.parameter > 999:
            self.parameter = 1
        d = self.writeParameter(1, 1, self.parameter)
        d.addCallback(self.printMessage)
        d.addErrback(self.errorHandler,"Error in sendMessage")
        self.parameter += 1

    def printMessage(self, data):
        print "Parameter: ", data.parameter, " Returned: ", data.Data
        reactor.callLater(1,self.sendMessage)


#---------------------------------------------------------------------------# 
# a factory for the protocol
#---------------------------------------------------------------------------# 
# This is used to build client protocol's if you tie into twisted's method
# of processing. It basically produces client instances of the underlying
# protocol::
#
#     Factory(Protocol) -> ProtocolInstance
#
# It also persists data between client instances (think protocol singelton).
#---------------------------------------------------------------------------# 
class MTrimFactory(ClientFactory):

    protocol = MTrimProtocol

    def __init__(self, framer):
        ''' Remember things necessary for building a protocols '''
        self.framer = framer

    def buildProtocol(self):
        ''' Create a protocol and start the reading cycle '''
        proto = self.protocol(self.framer)
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
class SerialMTrimClient(serialport.SerialPort):

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
# An example line reader, this can replace with:
# - the TCP protocol
# - a context recorder
# - a database or file recorder
#---------------------------------------------------------------------------# 
class LoggingLineReader(object):

    def write(self, response):
        ''' Handle the next modbus response

        :param response: The response to process
        '''
        log.info("Read Data: %d" % response)

#---------------------------------------------------------------------------# 
# start running the processor
#---------------------------------------------------------------------------# 
# This initializes the client, the framer, the factory, and starts the
# twisted event loop (the reactor). It should be noted that a number of
# things could be chanegd as one sees fit:
# - The AsciiFramer could be replaced with a SocketFramer
# - The SerialClient could be replaced with reactor.connectTCP
# - The LineReader endpoint could be replaced with a database store
#---------------------------------------------------------------------------# 
def main():
    log.debug("Initializing the client")

    options = Options()
    config = SafeConfigParser()
    config.read([options['config']])

    framer = AsciiFramer(ClientDecoder())
    factory = MTrimFactory(framer)

    RS422port = config.get('RS-422', 'host')
    RS422baud = config.getint('RS-422', 'baudrate')

    SerialMTrimClient(factory, RS422port, reactor, baudrate = RS422baud)

    log.debug("Starting the client")

    reactor.run()

if __name__ == "__main__":
    main()
