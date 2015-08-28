from constants import Defaults
import struct
import utilities
from serialexceptions import CRCException

ELEMENT_SIZE = {
                0x84: 2,         #Status
                0x85: 2,         #Bit
                0x86: 6,         #Timer
                0x87: 6,         #Counter
                0x88: 2,         #Control
                0x89: 2,         #Integer
                0x8A: 4,         #Float
                0x8B: 2,         #Output
                0x8C: 2,         #Input
                0x8D: 82,        #String
                0x8E: 2,         #ASCII
                0x8F: 2,         #BCD
                0x91: 4,
                0x92: 50,        #Message
                0x93: 2,         #PID
                0x94: 2}        #Programmable Limit Switch



SUBELEMENT_SIZE = {
                0x84: 2,         #Status
                0x85: 2,         #Bit
                0x86: 2,         #Timer
                0x87: 2,         #Counter
                0x88: 2,         #Control
                0x89: 2,         #Integer
                0x8A: 4,         #Float
                0x8B: 2,         #Output
                0x8C: 2,         #Input
                0x8D: 2,        #String
                0x8E: 2,         #ASCII
                0x8F: 2,         #BCD
                0x91: 4,
                0x92: 50,        #Message
                0x93: 2,         #PID
                0x94: 2}        #Programmable Limit Switch

ELEMENT_STRUCT = {
                0x84: 'h',         #Status
                0x85: 'h',         #Bit
                0x86: 'hhh',       #Timer
                0x87: 'hhh',       #Counter
                0x88: 'h',         #Control
                0x89: 'h',         #Integer
                0x8A: 'f',         #Float
                0x8B: 'h',         #Output
                0x8C: 'h',         #Input
                0x8D: '82s',       #String
                0x8E: 'h',         #ASCII
                0x8F: 'h',         #BCD
                0x91: 'f',
                0x92: 'B'*50,      #Message
                0x93: 'h',         #PID
                0x94: 'h'}         #Programmable Limit Switch

SUBELEMENT_STRUCT = {
                0x84: 'h',         #Status
                0x85: 'h',         #Bit
                0x86: 'h',         #Timer
                0x87: 'h',         #Counter
                0x88: 'h',         #Control
                0x89: 'h',         #Integer
                0x8A: 'f',         #Float
                0x8B: 'h',         #Output
                0x8C: 'h',         #Input
                0x8D: '82s',       #String
                0x8E: 'h',         #ASCII
                0x8F: 'h',         #BCD
                0x91: 'f',
                0x92: 'h'*50,      #Message
                0x93: 'h',         #PID
                0x94: 'h'}         #Programmable Limit Switch


class PDU(object):
    '''
    Base class for all DF1 mesages

    .. attribute:: transaction_id

       This value is used to uniquely identify a request
       response pair.  It can be implemented as a simple counter

    .. attribute:: Source

       This is a constant set at 0 for serial communication.
       
    .. attribute:: Destination

       This is used to route the request to the correct device.
       The value 0x00 represents the broadcast address.

    .. attribute:: check

       This is used for LRC/CRC in the serial modbus protocols

    .. attribute:: skip_encode

       This is used when the message payload has already been encoded.
       Generally this will occur when the PayloadBuilder is being used
       to create a complicated message. By setting this to True, the
       request will pass the currently encoded message through instead
       of encoding it again.
    '''

    def __init__(self, **kwargs):
        ''' Initializes the base data for a modbus request '''
        self.transaction_id = kwargs.get('transaction', Defaults.TransactionId)
        self.skip_encode = kwargs.get('skip_encode', False)

    def encode(self):
        ''' Encodes the message

        :raises: A not implemented exception
        '''
        pass

    def decode(self, data):
        ''' Decodes data part of the message.

        :param data: is a string object
        :raises: A not implemented exception
        '''
        pass

    @classmethod
    def calculateRtuFrameSize(cls, buffer):
        ''' Calculates the size of a PDU.

        :param buffer: A buffer containing the data that have been received.
        :returns: The number of bytes in the PDU.
        '''
        if hasattr(cls, '_rtu_frame_size'):
            return cls._frame_size
        elif hasattr(cls, '_byte_count_pos'):
            return rtuFrameSize(buffer, cls._byte_count_pos)
        else: raise NotImplementedException(
            "Cannot determine RTU frame size for %s" % cls.__name__)


class protectedReadRequest(PDU):
    '''
    Base class for reading a PLC register
    '''
    _frame_size = 18
    cmd = 0x0F
    function = 0xA2

    def __init__(self, dest, parameter, size=1, packet='', src=0, **kwargs):
        ''' Initializes a new instance

        :param address: The destination PLC address
        :param parameter: The PLC address to read
        :param size: The number of elements to read
        :param packet: Used when we already have an encoded packet
        '''
        PDU.__init__(self, **kwargs)
        self.src = src
        self.dest = dest
        self.parameter = parameter
        self.sts = 0x00
        self.size = size
        self.Address = utilities.calcAddress(parameter)
        self.packet = packet
        
    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''
        if (not self.skip_encode):
            ############################
            # Packet Start Sequence
            ############################
            self.packet = struct.pack('>BB', 0x10, 0x02)        #DLE STX

            ############################
            # Packet Header Information
            ############################
            data = struct.pack('>BBBBHB', self.dest,
                                          self.src,
                                          self.cmd,
                                          self.sts,
                                          self.transaction_id,
                                          self.function)
            if (self.Address.subElement > 0):
                elementSize = SUBELEMENT_SIZE[self.Address.fileType]*self.size
            else:
                elementSize = ELEMENT_SIZE[self.Address.fileType]*self.size
                
            data += struct.pack('>B', elementSize)

            ###################################################
            # Packet Address Information
            # Note: Use Little Endian format if using 2 bytes
            ###################################################
            if (self.Address.fileNumber > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.fileNumber)

            else:
                data += struct.pack('>B', self.Address.fileNumber)

            data += struct.pack('>B', self.Address.fileType)

            if (self.Address.eleNumber > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.eleNumber)
            else:
                data += struct.pack('>B', self.Address.eleNumber)

            if (self.Address.subElement > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.subElement)
            else:
                data += struct.pack('>B', self.Address.subElement)

            #######################################
            # Calculate CRC before escaping DLE's
            #######################################
            crc = utilities.computeCRC(data)

            ####################################
            # Escape any DLE's ('\x10') in data
            ####################################
            start = 0
            while (data.find('\x10', start, len(data)) != -1):
                i = data.find('\x10', start, len(data))
                data = data[:i] + '\x10' + data[i:]
                start = i+2

            self.packet += data

            ###################################
            # Packet End
            ###################################
            self.packet += struct.pack('>BB', 0x10,0x03)        #DLE ETX
            self.packet += struct.pack('>H', crc)
        else:
            self.packet = packet

        return self.packet

    def decode(self, packet):
        ''' Decode a register request packet

        :param packet: The packet to decode
        '''

        #############################################
        # Calculate CRC after removing stx/etx words
        #############################################
        data = packet[2:-3]
        packetCRC = packet[-2:]
        if (utilities.checkCRC(data, packetCRC) != True):
            raise CRCException

        
        ############################
        # Packet Header Information
        ############################
        self.dest, self.src, self.cmd, self.sts, self.transaction_id = struct.unpack('>BBBBH', data[0:6])
        self.function,self.size = struct.unpack('>BB', packet[6:8])
        data = data[8:]

        ###################################################
        # Packet Address Information
        # Note: Use Little Endian format if using 2 bytes
        ###################################################
        self.Address.fileNumber = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.fileNumber == '\xFF'):
            self.Address.fileNumber = struct.unpack('<H', data[0:2])
            data = data[2:]

        self.Address.fileType = struct.unpack('>B', data[0])
        data = data[1:]

        self.Address.eleNumber = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.eleNumber == '\xFF'):
            self.Address.eleNumber = struct.unpack('<H', packet[0:2])
            data = data[2:]

        self.Address.subElement = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.subElement == '\xFF'):
            self.Address.subElement = struct.unpack('<H', packet[0:2])
           
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "DataInquiryRequest (%s,%s)" % (self.dest, self.parameter)

class protectedWriteRequest(PDU):
    '''
    Base class for reading a PLC register
    '''
    _frame_size = 12
    cmd = 0x0F
    function = 0xAA

    def __init__(self, dest=0, parameter=None, values=None, size=1, src=0, **kwargs):
        ''' Initializes a new instance

        :address: The address of the PLC to communicate with
        :parameter: The parameter address to begin writing to
        :values: a list of values to write
        :size: The number of bytes to write
        '''
        PDU.__init__(self, **kwargs)
        self.src = 0
        self.dest = dest
        self.parameter = parameter
        self.values = values
        self.sts = 0x00
        self.size = size
        self.Address = utilities.calcAddress(parameter)
        self.packet = ''

    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''

        if (not self.skip_encode):
            ############################
            # Packet Start Sequence
            ############################
            self.packet = struct.pack('>BB', 0x10, 0x02)        #DLE STX

            ############################
            # Packet Header Information
            ############################
            data = struct.pack('>BBBBHB', self.dest,  self.src, self.cmd, self.sts, self.transaction_id, self.function)

            if (self.Address.subElement > 0):
                elementSize = SUBELEMENT_SIZE[self.Address.fileType]*self.size
            else:
                elementSize = ELEMENT_SIZE[self.Address.fileType]*self.size
                
            data += struct.pack('>B', elementSize)

            ###################################################
            # Packet Address Information
            # Note: Use Little Endian format if using 2 bytes
            ###################################################
            if (self.Address.fileNumber > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.fileNumber)

            else:
                data += struct.pack('>B', self.Address.fileNumber)

            data += struct.pack('>B', self.Address.fileType)

            if (self.Address.eleNumber > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.eleNumber)
            else:
                data += struct.pack('>B', self.Address.eleNumber)

            if (self.Address.subElement > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.subElement)
            else:
                data += struct.pack('>B', self.Address.subElement)

            
            ##############################################
            # Add Data Values using Little Endian format
            ##############################################
            if (self.Address.subElement > 0):
                formatStr = '<' + SUBELEMENT_STRUCT[self.Address.fileType]
            else:
                formatStr = '<' + ELEMENT_STRUCT[self.Address.fileType]

            for value in self.values:
                if (self.Address.subElement > 0):
                    data += struct.pack(formatStr, value)
                else:                                   # Everything else is 16 bits
                    data += struct.pack(formatStr, value)
            #######################################
            # Calculate CRC before escaping DLE's
            #######################################
            crc = utilities.computeCRC(data)

            ####################################
            # Escape any DLE's ('\x10') in data
            ####################################
            start = 0
            while (data.find('\x10', start, len(data)) != -1):
                i = data.find('\x10', start, len(data))
                data = data[:i] + '\x10' + data[i:]
                start = i+2

            self.packet += data

            ###################################
            # Packet End
            ###################################
            self.packet += struct.pack('>BB', 0x10,0x03)        #DLE ETX
            self.packet += struct.pack('>H', crc)     

        else:
                self.packet = packet
                
        return self.packet

    def decode(self, packet):
        ''' Decode a register request packet

        :param data: The request to decode
        '''
        ########################################################
        # Unescape any DLE's ('\x10') in data
        # Do not include DLE STX and DLE ETX CRC in calcualtion
        ########################################################
        print repr(packet)
        data = packet[2:-3]
        while (data.find('\x10') != -1):
            i = data.find('\x10')
            data = data[:i] + data[i+1:]
        
        #############################################
        # Calculate CRC after removing escaped DLE's
        #############################################
        #crc = utilities.computeCRC(data)
        #if (utilities.computeCRC(data, packet[-2:]) != True):
        #    print "CRC's: ", repr(crc), "  ", repr(packet[-2:])
        #    raise CRCException

        
        ############################
        # Packet Header Information
        ############################
        self.dest,  self.src, self.cmd, self.sts, self.transaction_id = struct.unpack('>BBBBH', data[0:6])
        self.function,self.size = struct.unpack('>BB', packet[6:8])
        data = data[8:]

        ###################################################
        # Packet Address Information
        # Note: Use Little Endian format if using 2 bytes
        ###################################################
        self.Address.fileNumber = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.fileNumber == '\xFF'):
            self.Address.fileNumber = struct.unpack('<H', data[0:2])
            data = data[2:]

        self.Address.fileType = struct.unpack('>B', data[0])
        data = data[1:]

        self.Address.eleNumber = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.eleNumber == '\xFF'):
            self.Address.eleNumber = struct.unpack('<H', packet[0:2])
            data = data[2:]

        self.Address.subElement = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.subElement == '\xFF'):
            self.Address.subElement = struct.unpack('<H', packet[0:2])
            data = data[2:]

        ######################################################
        # Packet Data Information using Little Endian format
        ######################################################
        if (self.Address.subElement > 0):
            elementSize = SUBELEMENT_SIZE[self.Address.fileType]
            formatStr = '<' + SUBELEMENT_STRUCT[self.Address.fileType]
        else:
            elementSize = ELEMENT_SIZE[self.Address.fileType]
            formatStr = '<' + ELEMENT_STRUCT[self.Address.fileType]

        self.values = ()
        item = 0            
        for i in range(0, len(data), elementSize):
            self.values += struct.unpack(formatStr, data[i:i+elementSize])
            item += 1
        
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "protetedWriteRequest (%d,%d,%d)" % (self.address, self.parameter, self.values)

class protectedBitWriteRequest(PDU):
    '''
    Base class for reading a PLC register
    '''
    _frame_size = 12
    cmd = 0x0F
    function = 0xAB

    def __init__(self, dest=0, parameter=None, values=None, size=1, src=0, **kwargs):
        ''' Initializes a new instance

        :address: The address of the PLC to communicate with
        :parameter: The parameter address to begin writing to
        :values: a list of values to write
        :size: The number of bytes to write
        '''
        PDU.__init__(self, **kwargs)
        self.src = 0
        self.dest = dest
        self.parameter = parameter
        self.values = values
        self.sts = 0x00
        self.size = size
        self.Address = utilities.calcAddress(parameter)
        self.packet = ''
        self.mask = 0

    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''

        if (not self.skip_encode):
            ############################
            # Packet Start Sequence
            ############################
            self.packet = struct.pack('>BB', 0x10, 0x02)        #DLE STX

            ############################
            # Packet Header Information
            ############################
            data = struct.pack('>BBBBHB', self.dest,  self.src, self.cmd, self.sts, self.transaction_id, self.function)

            if (self.Address.subElement > 0):
                elementSize = SUBELEMENT_SIZE[self.Address.fileType]*self.size
            else:
                elementSize = ELEMENT_SIZE[self.Address.fileType]*self.size
                
            data += struct.pack('>B', elementSize)

            ###################################################
            # Packet Address Information
            # Note: Use Little Endian format if using 2 bytes
            ###################################################
            if (self.Address.fileNumber > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.fileNumber)

            else:
                data += struct.pack('>B', self.Address.fileNumber)

            data += struct.pack('>B', self.Address.fileType)

            if (self.Address.eleNumber > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.eleNumber)
            else:
                data += struct.pack('>B', self.Address.eleNumber)

            if (self.Address.subElement > 254):
                data += struct.pack('>B', 0xFF)
                data += struct.pack('<H', self.Address.subElement)
            else:
                data += struct.pack('>B', self.Address.subElement)

            if (self.Address.bitNumber != None):
                mask = 0xFFFF & 2**self.Address.bitNumber
                data += struct.pack('<H', mask)
            
            ##############################################
            # Add Data Values using Little Endian format
            ##############################################
            if (self.Address.subElement > 0):
                formatStr = '<' + SUBELEMENT_STRUCT[self.Address.fileType]
            else:
                formatStr = '<' + ELEMENT_STRUCT[self.Address.fileType]

            for value in self.values:
                if (self.Address.subElement > 0):
                    data += struct.pack(formatStr, value)
                else:                                   # Everything else is 16 bits
                    data += struct.pack(formatStr, value)
            #######################################
            # Calculate CRC before escaping DLE's
            #######################################
            crc = utilities.computeCRC(data)

            ####################################
            # Escape any DLE's ('\x10') in data
            ####################################
            start = 0
            while (data.find('\x10', start, len(data)) != -1):
                i = data.find('\x10', start, len(data))
                data = data[:i] + '\x10' + data[i:]
                start = i+2

            self.packet += data

            ###################################
            # Packet End
            ###################################
            self.packet += struct.pack('>BB', 0x10,0x03)        #DLE ETX
            self.packet += struct.pack('>H', crc)     

        else:
                self.packet = packet
                
        return self.packet

    def decode(self, packet):
        ''' Decode a register request packet

        :param data: The request to decode
        '''
        ########################################################
        # Unescape any DLE's ('\x10') in data
        # Do not include DLE STX and DLE ETX CRC in calcualtion
        ########################################################
        print repr(packet)
        data = packet[2:-3]
        while (data.find('\x10') != -1):
            i = data.find('\x10')
            data = data[:i] + data[i+1:]
        
        #############################################
        # Calculate CRC after removing escaped DLE's
        #############################################
        #crc = utilities.computeCRC(data)
        #if (utilities.computeCRC(data, packet[-2:]) != True):
        #    print "CRC's: ", repr(crc), "  ", repr(packet[-2:])
        #    raise CRCException

        
        ############################
        # Packet Header Information
        ############################
        self.dest,  self.src, self.cmd, self.sts, self.transaction_id = struct.unpack('>BBBBH', data[0:6])
        self.function,self.size = struct.unpack('>BB', packet[6:8])
        data = data[8:]

        ###################################################
        # Packet Address Information
        # Note: Use Little Endian format if using 2 bytes
        ###################################################
        self.Address.fileNumber = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.fileNumber == '\xFF'):
            self.Address.fileNumber = struct.unpack('<H', data[0:2])
            data = data[2:]

        self.Address.fileType = struct.unpack('>B', data[0])
        data = data[1:]

        self.Address.eleNumber = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.eleNumber == '\xFF'):
            self.Address.eleNumber = struct.unpack('<H', packet[0:2])
            data = data[2:]

        self.Address.subElement = struct.unpack('>B', data[0])
        data = data[1:]
        if (self.Address.subElement == '\xFF'):
            self.Address.subElement = struct.unpack('<H', packet[0:2])
            data = data[2:]

        self.mask = struct.unpack('<H', data[0:2])
        data = data[2:]
        
        ######################################################
        # Packet Data Information using Little Endian format
        ######################################################
        if (self.Address.subElement > 0):
            elementSize = SUBELEMENT_SIZE[self.Address.fileType]
            formatStr = '<' + SUBELEMENT_STRUCT[self.Address.fileType]
        else:
            elementSize = ELEMENT_SIZE[self.Address.fileType]
            formatStr = '<' + ELEMENT_STRUCT[self.Address.fileType]
                
        self.values = ()
        item = 0            
        for i in range(0, len(data), elementSize):
            self.values += struct.unpack(formatStr, data[i:i+elementSize])
            item += 1
        
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "protetedWriteRequest (%d,%d,%d)" % (self.address, self.parameter, self.values)


class Command_0F_Response(PDU):
    '''
    The normal response is a series of 'sub-responses,' one for each
    'sub-request.' The byte count field is the total combined count of
    bytes in all 'sub-responses.' In addition, each 'sub-response'
    contains a field that shows its own byte count.
    '''
    cmd = 0x4F
    function = None
    _rtu_byte_count_pos = 2

    def __init__(self, request, dest=1, src=0, sts=0, tid=0, records=None, **kwargs):
        ''' Initializes a new instance

        :param records: The requested file records
        '''
        PDU.__init__(self, **kwargs)
        self.dest = dest
        self.src = src
        self.sts = sts
        self.tid = tid
        self.crc = 0
        self.frame=''
        self.records = records or []
        self.Address = request.Address

    def encode(self):
        ''' Encodes the response

        :returns: The byte encoded message
        '''
        ############################
        # Packet Start Sequence
        ############################
        self.frame = struct.pack('>BB', 0x10, 0x02)        #DLE STX

        ############################
        # Packet Header Information
        ############################
        data = struct.pack('>BBBBHB', self.dest,  self.src, self.cmd, self.sts, self.transaction_id)

        if (self.Address.subElement > 0):
            elementSize = SUBELEMENT_SIZE[self.Address.fileType]
            formatStr = '<' + SUBELEMENT_STRUCT[self.Address.fileType]
        else:
            elementSize = ELEMENT_SIZE[self.Address.fileType]
            formatStr = '<' + ELEMENT_STRUCT[self.Address.fileType]
                
        for record in self.records:
            data += struct.pack(formatStr, record)
                
        #######################################
        # Calculate CRC before escaping DLE's
        #######################################
        crc = utilities.computeCRC(data)

        ####################################
        # Escape any DLE's ('\x10') in data
        ####################################
        start = 0
        while (data.find('\x10', start, len(data)) != -1):
            i = data.find('\x10', start, len(data))
            data = data[:i] + '\x10' + data[i:]
            start = i+2

        self.frame += data

        ###################################
        # Packet End
        ###################################
        self.frame += struct.pack('>BB', 0x10, 0x03)        #DLE ETX
        self.frame += struct.pack('>H', crc)                #crc

        return self.frame

    def decode(self, packet):
        ''' Decodes a the response

        :param packet: The packet data to decode
        '''
        count, self.records = 1, []

        self.frame = packet
        ########################################################
        # Do not include DLE STX and DLE ETX CRC in calcualtion
        ########################################################
        data = packet[2:-4]
        
        #############################################
        # Calculate CRC after removing escaped DLE's
        #############################################
        crc, = struct.unpack('>H', packet[-2:])
        if (utilities.checkCRC(data, crc) != True):
            raise CRCException("Error in CRC : %d" % crc)

        
        ############################
        # Packet Header Information
        ############################
        self.dest,  self.src, self.command, self.sts, self.transaction_id = struct.unpack('>BBBBH', data[0:6])
        data = data[6:]

        #####################################
        # Packet data Information
        # Use Little Endian format for data
        #####################################
        self.records = ()
        if len(data)>0:
            if (self.Address.subElement > 0):
                elementSize = SUBELEMENT_SIZE[self.Address.fileType]
                formatStr = '<' + SUBELEMENT_STRUCT[self.Address.fileType]
            else:
                elementSize = ELEMENT_SIZE[self.Address.fileType]
                formatStr = '<' + ELEMENT_STRUCT[self.Address.fileType]
               
            for i in range(0, len(data), elementSize):
                if (self.Address.bitNumber != None):
                    register, = struct.unpack(formatStr, data[i:i+elementSize])
                    if (register & 2**self.Address.bitNumber):
                        self.records += (1,)
                    else:
                        self.records += (0,)
                else:
                    if (self.Address.fileType == 0x8D):
                        record, = struct.unpack(formatStr, data[i:i+elementSize])
                        size, = struct.unpack('<h',record[0:2])
                        newRecord = ""
                        for i in range(2, elementSize, 2):
                            newRecord += record[i+1] + record[i]
                        self.records += (newRecord[0:size],)
                    else:
                        self.records += struct.unpack(formatStr, data[i:i+elementSize])
  

            self.records = utilities.flatten(self.records)
        else:
            self.records = None
                   
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "DataInquiryRequest (%d,%d)" % (self.command, self.sts)


class ControlCommandSendRequest(PDU):
    '''
    Base class for reading a DF1 register
    '''
    _frame_size = 12

    def __init__(self, address, value, **kwargs):
        ''' Initializes a new instance

        :param address: The address to start the read from
        :param value: The number of registers to read
        '''
        PDU.__init__(self, **kwargs)
        self.address = address
        self.parameter = '00'
        self.msgType = '1'
        self.value = value
        self.Data = ''
        self.dataFormat = '0'
        self.packet = ''

    def encode(self):
        ''' Encodes the request packet

        :return: The encoded packet
        '''
        if (not self.skip_encode):
            self.packet = struct.pack('>B', 0x02)        #STX
            if (self.address <10):
                self.packet += '0' + str(self.address)
            else:
                self.packet += str(self.address)

            self.packet += self.msgType

            self.packet += self.parameter

            self.packet += '00'
            if (self.value<10):
                self.packet += '0' + str(self.value)
            else:
                self.packet += str(self.value)
                    
            self.packet += self.dataFormat
            self.packet += struct.pack('>B', 0x03)       #ETX
                        
        return self.packet

    def decode(self, data):
        ''' Decode a register request packet

        :param data: The request to decode
        '''
        self.address = int(data[1])*10 + int(data[2])
        self.msgType = int(data[3])
        self.parameter = int(data[4])*10 + int(data[5])
        self.dataFormat = int(data[10])

        self.value = int(data[6:10])
        if (self.dataFormat <= 3):
            self.Data = self.value/(10*self.dataFormat)
        else:
            self.Data = -1 * self.value/(10*self.dataFormat)
        
    def __str__(self):
        ''' Returns a string representation of the instance

        :returns: A string representation of the instance
        '''
        return "ControlCommandSendRequest (%d,%d,%d)" % (self.address, self.Data)
